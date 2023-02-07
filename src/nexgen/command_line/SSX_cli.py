"""
Command line tool to generate NXmx NeXus files for Serial Crystallography.
"""

import argparse
import logging
from pathlib import Path
from typing import Tuple

from .. import P, log
from . import version_parser

logger = logging.getLogger("nexgen.SSX_cli")

usage = "%(prog)s <sub-command> collection-data [options]"
parser = argparse.ArgumentParser(
    usage=usage, description=__doc__, parents=[version_parser]
)
parser.add_argument("--debug", action="store_const", const=True)

# This might be better passed as a json/yaml or whatever
CHIP_DICT = {
    "X_NUM_STEPS": [0, 20],
    "Y_NUM_STEPS": [0, 20],
    "X_STEP_SIZE": [0, 0.125],
    "Y_STEP_SIZE": [0, 0.125],
    "X_START": [0, 0],
    "Y_START": [0, 0],
    "Z_START": [0, 0],
    "X_NUM_BLOCKS": [0, 8],
    "Y_NUM_BLOCKS": [0, 8],
    "X_BLOCK_SIZE": [0, 3.175],
    "Y_BLOCK_SIZE": [0, 3.175],
}


def eiger_collection(args):
    print(args)


def tristan_collection(args):
    print(args)


# Define a parser for the basic collection parameters
class _ImportCollect(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        input_file, visitpath, filename_root = self.find_import_args(values)
        setattr(namespace, self.dest, input_file)
        setattr(namespace, "visitpath", visitpath)
        setattr(namespace, "filename_root", filename_root)

    @staticmethod
    def find_import_args(val) -> Tuple[str]:
        input_file = Path(val).expanduser().resolve()
        visitpath = input_file.parent
        filename_root = P.fullmatch(input_file.stem)[1]
        return input_file, visitpath, filename_root


collect_parser = argparse.ArgumentParser(add_help=False)
# Get visitpath and filename_root out of meta file
collect_parser.add_argument(
    "input_file",
    type=str,
    action=_ImportCollect,
    help="Path to _meta.h5 or _000001.h5 file.",
)
collect_parser.add_argument("beamline", type=str, help="Beamline name.")
collect_parser.add_argument(
    "-e",
    "--exp-time",
    type=float,
    help="Exxposure time in s.",
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
    "-p",
    "--pump-status",
    action="store_true",
    default=False,
    help="Select pump status.",
)
eiger_parser.add_argument("--chipmap", typ=str, help="Location of chipmap.")
eiger_parser.set_defaults(func=eiger_collection)

tristan_parser = subparsers.add_parser(
    "2",
    aliases=["tristan"],
    description=("Trigger Tristan writer."),
    parents=[collect_parser],
)
tristan_parser.add_argument("--chipmap", typ=str, help="Location of chipmap.")
tristan_parser.set_defaults(func=tristan_collection)


def main():
    log.config()
    args = parser.parse_args()
    args.func(args)
