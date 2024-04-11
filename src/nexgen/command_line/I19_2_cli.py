"""
Command line interface to create a NeXus file for time-resolved collections on I19-2.
Available detectors: Tristan 10M, Eiger 2X 4M.
"""

import argparse
import logging
from collections import namedtuple
from datetime import datetime

from .. import log
from . import version_parser

logger = logging.getLogger("nexgen.I19-2_NeXus_cli")

usage = "%(prog)s <sub-command> [options]"
parser = argparse.ArgumentParser(
    usage=usage, description=__doc__, parents=[version_parser]
)
parser.add_argument("--debug", action="store_const", const=True)


def gda_writer(args):
    """
    Write a NeXus file starting from information passed by GDA.
    """
    logger.info("Create a NeXus file for I19-2 interfacing with GDA.")

    from ..beamlines.I19_2_gda_nxs import write_nxs

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
        ),  # datetime.now(),
        geometry_json=args.geom if args.geom else None,
        detector_json=args.det if args.det else None,
    )


def nexgen_writer(args):
    """
    Write a NXmx format NeXus file from the I19-2 beamline.
    """
    logger.info("Create a NeXus file for I19-2 data.")

    from ..beamlines.I19_2_nxs import axes, det_axes, nexus_writer

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

    if args.axes and args.ax_start:
        if args.detector_name == "eiger":
            axes_list = []
            for ax, s, i in zip(args.axes, args.ax_start, args.ax_inc):
                axes_list.append(axes(id=ax, start=s, inc=i))
        else:
            axes = namedtuple("axes", ("id", "start", "end"))
            axes_list = []
            for ax, s, e in zip(args.axes, args.ax_start, args.ax_end):
                axes_list.append(axes(id=ax, start=s, end=e))

    if args.det_axes and args.det_start:
        det_list = []
        for ax, s in zip(args.det_axes, args.det_start):
            det_list.append(det_axes(id=ax, start=s))

    # Check that an actual meta file has been passed and not a data file
    if "meta" not in args.meta_file:
        logger.error(
            f"Wrong input file passed: {args.meta_file}. Please pass the _meta.h5 file for this dataset."
        )
        raise OSError(
            "The input file passed is not a _meta.h5 file. Please pass the correct file."
        )

    nexus_writer(
        meta_file=args.meta_file,
        detector_name=args.detector_name,
        exposure_time=args.exp_time,
        transmission=args.transmission if args.transmission else None,
        wavelength=args.wavelength if args.wavelength else None,
        beam_center=args.beam_center if args.beam_center else (0, 0),
        start_time=(
            datetime.strptime(args.start, "%Y-%m-%dT%H:%M:%SZ") if args.start else None
        ),
        stop_time=(
            datetime.strptime(args.stop, "%Y-%m-%dT%H:%M:%SZ") if args.stop else None
        ),
        n_imgs=args.num_imgs if args.num_imgs else None,
        scan_axis=args.scan_axis if args.scan_axis else "phi",
        gonio_pos=axes_list if args.axes else None,
        det_pos=det_list if args.det_axes else None,
        outdir=args.output if args.output else None,
        use_meta=args.use_meta,
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
    "--start", "--start-time", type=str, default=None, help="Collection start time."
)
parser_gda.add_argument(
    "--stop", "--stop-time", type=str, default=None, help="Collection end time."
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
    parents=[gonioAx_parser, detAx_parser],
)
parser_nex.add_argument("meta_file", type=str, help="Path to _meta.h5 file.")
parser_nex.add_argument(
    "detector_name", type=str, help="Detector currently in use on beamline."
)
parser_nex.add_argument("exp_time", type=float, help="Exposure time, in s.")
parser_nex.add_argument(
    "-n",
    "--num_imgs",
    type=int,
    default=None,
    help="Number of frames collected. Necessary for eiger if not using meta file.",
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
    "--start", "--start-time", type=str, default=None, help="Collection start time."
)
parser_nex.add_argument(
    "--stop", "--stop-time", type=str, default=None, help="Collection end time."
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
parser_nex.set_defaults(func=nexgen_writer)


def main():
    log.config()
    args = parser.parse_args()
    args.func(args)
