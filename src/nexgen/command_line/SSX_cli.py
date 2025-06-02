"""
Command line tool to generate NXmx NeXus files for Serial Crystallography on I24.
"""

import argparse
import logging
from pathlib import Path

from .. import log
from ..beamlines.SSX_chip import CHIP_DICT_DEFAULT
from ..beamlines.SSX_Eiger_nxs import ssx_eiger_writer
from .parse_utils import ImportCollectAction, version_parser

logger = logging.getLogger("nexgen.SSX_cli")

usage = "%(prog)s <sub-command> collection_meta.h5 [options]"
parser = argparse.ArgumentParser(
    usage=usage, description=__doc__, parents=[version_parser]
)


def eiger_collection(args):
    logger.info("Create a NeXus file for SSX collection on Eiger.")

    ssx_eiger_writer(
        Path(args.visitpath).expanduser().resolve(),
        args.filename_root,
        "I24",
        expt_type=args.expt_type,
        pump_status=args.pump_status,
        num_imgs=args.num_imgs,
        exp_time=args.exp_time,
        det_dist=args.det_dist,
        beam_center=args.beam_center,
        transmission=args.transmission,
        wavelength=args.wavelength,
        start_time=args.start,
        stop_time=args.stop,
        chip_info=CHIP_DICT_DEFAULT,  # TODO This might be better passed as a json/yaml or whatever
        chipmap=args.chipmap,
    )


collect_parser = argparse.ArgumentParser(add_help=False)
# Get visitpath and filename_root out of meta file
collect_parser.add_argument(
    "input_file",
    type=str,
    action=ImportCollectAction,
    help="Path to _meta.h5 or _000001.h5 file.",
)
collect_parser.add_argument(
    "-det",
    "--det-dist",
    type=float,
    help="Detector distance in mm.",
)
collect_parser.add_argument(
    "-tr",
    "--transmission",
    type=float,
    default=None,
    help="Attenuator transmission.",
)
collect_parser.add_argument(
    "-wl",
    "--wavelength",
    type=float,
    default=None,
    help="Incident beam wavelength, in A.",
)
collect_parser.add_argument(
    "-bc",
    "--beam-center",
    type=float,
    nargs=2,
    default=[0.0, 0.0],
    help="Beam center (x,y) positions.",
)
collect_parser.add_argument(
    "--start", "--start-time", type=str, default=None, help="Collection start time."
)
collect_parser.add_argument(
    "--stop", "--stop-time", type=str, default=None, help="Collection end time."
)

# Define subparsers
subparsers = parser.add_subparsers(
    help="Choose the writer based on the Detector in use on the beamline. \
        Run SSX_nexus <command> --help to see the parameters for each sub-command.",
    required=True,
    dest="sub-command",
)

eiger_parser = subparsers.add_parser(
    "1",
    aliases=["eiger"],
    description=("Trigger Eiger writer."),
    parents=[collect_parser],
)
eiger_parser.add_argument(
    "expt_type",
    type=str,
    choices=["extruder", "fixed-target", "3Dgridscan"],
    help="Choose the type of serial experiment.",
)
eiger_parser.add_argument("num_imgs", type=int, help="Total number of images.")
eiger_parser.add_argument(
    "-e",
    "--exp-time",
    type=float,
    required=True,
    help="Exposure time in s.",
)
eiger_parser.add_argument(
    "-p",
    "--pump-status",
    action="store_true",
    default=False,
    help="Select pump status.",
)
eiger_parser.add_argument("--chipmap", type=int, nargs="+", help="Location of chipmap.")
eiger_parser.set_defaults(func=eiger_collection)


def main():
    log.config()
    args = parser.parse_args()
    args.func(args)
