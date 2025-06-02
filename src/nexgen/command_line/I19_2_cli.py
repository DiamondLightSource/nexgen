"""
Command line interface to create a NeXus file for time-resolved collections on I19-2.
Available detectors: Tristan 10M, Eiger 2X 4M.
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path

from nexgen.utils import get_nexus_filename

from .. import log
from ..beamlines.I19_2_gda_nxs import write_nxs
from ..beamlines.I19_2_nxs import (
    DetAxisPosition,
    GonioAxisPosition,
    nexus_writer,
    serial_nexus_writer,
)
from . import version_parser

logger = logging.getLogger("nexgen.I19-2_NeXus_cli")

usage = "%(prog)s <sub-command> [options]"
parser = argparse.ArgumentParser(
    usage=usage, description=__doc__, parents=[version_parser]
)


def gda_writer(args):
    """
    Write a NeXus file starting from information passed by GDA.
    """
    logger.info("Create a NeXus file for I19-2 interfacing with GDA.")

    write_nxs(
        meta_file=args.meta_file,
        xml_file=args.xml_file,
        detector_name=args.detector_name,  # e.g. "tristan", "eiger",
        exposure_time=float(args.exp_time),
        wavelength=float(args.wavelength),
        beam_center=[
            float(args.beam_center_x),
            float(args.beam_center_y),
        ],
        start_time=(
            datetime.strptime(args.start, "%Y-%m-%dT%H:%M:%SZ") if args.start else None
        ),
        stop_time=(
            datetime.strptime(args.stop, "%Y-%m-%dT%H:%M:%SZ") if args.stop else None
        ),
        geometry_json=args.geom if args.geom else None,
        detector_json=args.det if args.det else None,
    )


def parse_input_arguments(args):
    """Perform a series of checks on the nexgen CLI parsed arguments."""
    # Check that an actual meta file has been passed and not a data file
    if "meta" not in args.meta_file:
        logger.error(
            f"Wrong input file passed: {args.meta_file}. Please pass the _meta.h5 file for this dataset."
        )
        raise OSError(
            "The input file passed is not a _meta.h5 file. Please pass the correct file."
        )

    if args.axes and not args.ax_start:
        raise OSError(
            "Please pass start and increment values for each of the goniometer axes indicated."
        )
    if args.det_axes and not args.det_start:
        raise OSError(
            "Please pass start and increment values for each of the detector axes indicated."
        )

    if args.detector_name == "eiger" and not args.use_meta:
        if not args.axes or not args.det_axes:
            logger.error(
                "If not using the metadata from the meta_file please pass all axes values."
            )
            raise OSError("Missing axes values.")


def nexgen_writer(args):
    """
    Write a NXmx format NeXus file from the I19-2 beamline.
    """
    expt_type = "standard" if args.serial is False else "serial"
    logger.info(f"Create a NeXus file for a {expt_type} I19-2 data collection.")
    parse_input_arguments(args)

    axes_list = []
    det_list = []
    if args.axes and args.ax_start:
        if args.detector_name == "eiger":
            for ax, s, i in zip(args.axes, args.ax_start, args.ax_inc):
                axes_list.append(GonioAxisPosition(id=ax, start=s, inc=i))
        else:
            for ax, s, e in zip(args.axes, args.ax_start, args.ax_end):
                axes_list.append(GonioAxisPosition(id=ax, start=s, end=e))

    if args.det_axes and args.det_start:
        for ax, s in zip(args.det_axes, args.det_start):
            det_list.append(DetAxisPosition(id=ax, start=s))

    params = {
        "exposure_time": args.exp_time,
        "beam_center": args.beam_center if args.beam_center else (0, 0),
        "wavelength": args.wavelength if args.wavelength else None,
        "transmission": args.transmission if args.transmission else None,
        "metafile": args.meta_file,
        "detector_name": args.detector_name,
        "tot_num_images": args.num_imgs if args.num_imgs else None,
        "scan_axis": args.scan_axis if args.scan_axis else "phi",
        "axes_pos": axes_list if len(axes_list) > 0 else None,
        "det_pos": det_list if len(det_list) > 0 else None,
    }

    master_file = get_nexus_filename(args.meta_file)

    if args.outdir:
        _wdir = Path(args.outdir).expanduser().resolve()
        master_file = _wdir / master_file.name

    _start = datetime.strptime(args.start, "%Y-%m-%dT%H:%M:%SZ") if args.start else None
    _stop = datetime.strptime(args.stop, "%Y-%m-%dT%H:%M:%SZ") if args.stop else None

    if expt_type == "serial":
        serial_nexus_writer(
            params,
            master_file,
            (_start, _stop),
            args.use_meta,
            args.vds_offset,
            args.n_frames,
        )
    else:
        nexus_writer(
            params,
            master_file,
            (_start, _stop),
            args.use_meta,
        )


# Define a couple of useful parsers for axes positions
gonioAx_parser = argparse.ArgumentParser(add_help=False)
gonioAx_parser.add_argument("--axes", type=str, nargs="+", help="Axes names.")
gonioAx_parser.add_argument(
    "--ax-start", type=float, nargs="+", help="Axes start positions."
)
gonioAx_parser.add_argument(
    "--ax-inc", type=float, nargs="+", help="Eventual axes increments."
)
gonioAx_parser.add_argument(
    "--ax-end", type=float, nargs="+", help="Eventual axes ends."
)
gonioAx_parser.add_argument(
    "--scan-axis",
    type=str,
    default="phi",
    help="Identify scan axis. If not specified, defaults to phi.",
)

detAx_parser = argparse.ArgumentParser(add_help=False)
detAx_parser.add_argument(
    "--det-axes", type=str, nargs="+", help="Detector axes names."
)
detAx_parser.add_argument(
    "--det-start", type=float, nargs="+", help="Detector axes start positions."
)

timestamps_parser = argparse.ArgumentParser(add_help=False)
timestamps_parser.add_argument(
    "--start", "--start-time", type=str, default=None, help="Collection start time."
)
timestamps_parser.add_argument(
    "--stop", "--stop-time", type=str, default=None, help="Collection end time."
)

# Define subparsers
subparsers = parser.add_subparsers(
    help="Choice depending on how the data collection is run: from GDA or independently of it. \
        Run I19_nexus <command> --help to see the parameters for each sub-command.",
    required=True,
    dest="sub-command",
)

parser_gda = subparsers.add_parser(
    "1",
    aliases=["gda"],
    description=(
        "Trigger the NeXus file writer interface with GDA for I19-2 data collection."
    ),
    parents=[timestamps_parser],
)
parser_gda.add_argument("meta_file", type=str, help="Path to _meta.h5 file.")
parser_gda.add_argument("xml_file", type=str, help="Path to GDA generated xml file.")
parser_gda.add_argument(
    "detector_name",
    type=str,
    choices=["eiger", "tristan"],
    help="Detector currently in use on beamline.",
)
parser_gda.add_argument("exp_time", type=str, help="Exposure time, in s.")
parser_gda.add_argument("wavelength", type=str, help="Incident beam wavelength.")
parser_gda.add_argument(
    "beam_center_x", type=str, help="Beam center x position, in pixels."
)
parser_gda.add_argument(
    "beam_center_y", type=str, help="Beam center y position, in pixels."
)
parser_gda.add_argument(
    "--geom",
    "--geometry-json",
    type=str,
    default=None,
    help="Path to GDA generated geometry json file.",
)
parser_gda.add_argument(
    "--det",
    "--detector-json",
    type=str,
    default=None,
    help="Path to GDA generated detector json file.",
)
parser_gda.set_defaults(func=gda_writer)

parser_nex = subparsers.add_parser(
    "2",
    aliases=["gen"],
    description=("Trigger the NeXus file writer for I19-2 data collection."),
    parents=[gonioAx_parser, detAx_parser, timestamps_parser],
)
parser_nex.add_argument("meta_file", type=str, help="Path to _meta.h5 file.")
parser_nex.add_argument(
    "detector-name",
    type=str,
    choices=["eiger", "tristan"],
    help="Detector currently in use on beamline.",
)
parser_nex.add_argument("exp-time", type=float, help="Exposure time, in s.")
parser_nex.add_argument(
    "-n",
    "--num-imgs",
    type=int,
    default=None,
    help="Number of images collected. Necessary for eiger if not using meta file.",
)
parser_nex.add_argument(
    "-tr",
    "--transmission",
    type=float,
    default=None,
    help="Attenuator transmission.",
)
parser_nex.add_argument(
    "-wl",
    "--wavelength",
    type=float,
    default=None,
    help="Incident beam wavelength, in A.",
)
parser_nex.add_argument(
    "-bc",
    "--beam-center",
    type=float,
    nargs=2,
    help="Beam center (x,y) positions.",
)
parser_nex.add_argument(
    "-o",
    "--output",
    type=str,
    help="Output directory for new NeXus file, if different from collection directory.",
)
parser_nex.add_argument(
    "--use-meta",
    action="store_true",
    help="If passed, for Eiger metadata will be read from meta.h5 file. No action for Tristan.",
)
parser_nex.add_argument(
    "--serial", action="store_true", help="Option to pass for a serial dataset."
)
parser_nex.add_argument(
    "--vds-offset",
    type=int,
    default=0,
    help="Start index for the vds writer. Mostly used for serial collections to separate wells \
        into different nexus files. If not passed defaults to 0",
)
parser_nex.add_argument(
    "--frames",
    type=int,
    help="Number of frames in the nexus and vds file. Only passed if different from total number \
        of images collected.",
)
parser_nex.set_defaults(func=nexgen_writer)


def main():
    log.config()
    args = parser.parse_args()
    args.func(args)
