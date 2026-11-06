"""
Command line interface to create a NeXus file for time-resolved collections on I19-2.
Available detectors: Tristan 10M, Eiger 2X 4M.
"""

import argparse
import logging
from pathlib import Path

from nexgen.beamlines.i19_2 import (
    basic_nxmx_writer,
    gda_nexus_writer,
    serial_nexus_writer,
)
from nexgen.beamlines.i19_2.parameters import (
    DetAxisPosition,
    GonioAxisPosition,
    ParamsFromGDA,
)
from nexgen.command_line.parse_utils import vds_parser, version_parser
from nexgen.utils import get_nexus_filename

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

    params = ParamsFromGDA(
        metafile=args.meta_file,
        xmlfile=args.xml_file,
        detector_name=args.detector_name,
        exposure_time=args.exp_time,
        wavelength=args.wavelength,
        beam_center=(args.beam_center_x, args.beam_center_y),
        timestamps=(
            args.start if args.start else None,
            args.stop if args.stop else None,
        ),
        detector_params={"stream_format": args.eiger_format},
    )

    gda_nexus_writer(params)


def parse_input_arguments(args):
    """Perform a series of checks on the nexgen CLI parsed arguments."""
    # Check that an actual meta file has been passed and not a data file
    if "meta" not in args.meta_file:
        raise OSError(
            f"Wrong input file passed: {args.meta_file}. Please pass the _meta.h5 file for this dataset."
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
            raise OSError("Missing axes values when not using meta file.")


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
        "wavelength": args.wavelength,
        "transmission": args.transmission,
        "metafile": args.meta_file,
        "detector_name": args.detector_name,
        "tot_num_images": args.num_imgs if args.num_imgs else None,
        "scan_axis": args.scan_axis,
        "axes_pos": axes_list if len(axes_list) > 0 else None,
        "det_pos": det_list if len(det_list) > 0 else None,
        "timestamps": (
            args.start if args.start else None,
            args.stop if args.stop else None,
        ),
    }

    det_params = {
        "bit_depth": args.bit_depth,
        "data_entry_key": args.data_entry_key,
        "stream_format": args.eiger_format,
        "vds_offset": args.vds_offset,
        "vds_mapping": args.vds_mapping,
    }

    match expt_type:
        case "serial":
            master_file = get_nexus_filename(args.meta_file)

            if args.outdir:
                _wdir = Path(args.outdir).expanduser().resolve()
                master_file = _wdir / master_file.name

            serial_nexus_writer(params, master_file, det_params)
        case "standard":
            basic_nxmx_writer(params, det_params)


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
parser_gda.add_argument("exp_time", type=float, help="Exposure time, in s.")
parser_gda.add_argument("wavelength", type=float, help="Incident beam wavelength.")
parser_gda.add_argument(
    "beam_center_x", type=float, help="Beam center x position, in pixels."
)
parser_gda.add_argument(
    "beam_center_y", type=float, help="Beam center y position, in pixels."
)
parser_gda.add_argument(
    "--eiger-format",
    type=str,
    choices=["legacy", "cbor"],
    default="legacy",
    help="Eiger stream format. Defaults to legacy.",
)
parser_gda.set_defaults(func=gda_writer)

parser_nex = subparsers.add_parser(
    "2",
    aliases=["gen"],
    description=("Trigger the NeXus file writer for I19-2 data collection."),
    parents=[gonioAx_parser, detAx_parser, timestamps_parser, vds_parser],
)
parser_nex.add_argument("meta_file", type=str, help="Path to _meta.h5 file.")
parser_nex.add_argument(
    "detector_name",
    type=str,
    choices=["eiger", "tristan"],
    help="Detector currently in use on beamline.",
)
parser_nex.add_argument("exp_time", type=float, help="Exposure time, in s.")
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
    default=100,
    help="Attenuator transmission. Defaults to 100% if not passed.",
)
parser_nex.add_argument(
    "-wl",
    "--wavelength",
    type=float,
    default=0.649,
    help="Incident beam wavelength, in A. Defaults to 0.649 if not passed.",
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
    "--frames",
    type=int,
    help="Number of frames in the nexus and vds file. Only passed if different from total number \
        of images collected.",
)
parser_nex.add_argument(
    "--data-key",
    type=str,
    default="data",
    help="Data entry key of dataset in raw .h5 file. Defaults to data.",
)
parser_nex.add_argument(
    "-bits",
    "--bit-depth",
    type=int,
    choices=[8, 16, 32],
    default=32,
    help="Default bit depth for eiger collections, used to define dtype of vds data. Defaults to 32.",
)
parser_nex.add_argument(
    "--eiger-format",
    type=str,
    choices=["legacy", "cbor"],
    default="legacy",
    help="Eiger stream format. Defaults to legacy.",
)
parser_nex.set_defaults(func=nexgen_writer)


def main():
    args = parser.parse_args()
    args.func(args)
