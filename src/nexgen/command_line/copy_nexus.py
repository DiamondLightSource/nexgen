"""
Command line tool to copy experiment metadata from one NeXus file to the other.
"""

import sys
import logging
import argparse
import freephil

# from pathlib import Path

from . import (
    version_parser,
    full_copy_parser,
    tristan_copy_parser,
)

# from ..nxs_copy import CopyNexus, CopyTristanNexus

# Define a logger object and a formatter
logger = logging.getLogger("CopyNeXus")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s %(message)s")

# Phil scopes
general_scope = freephil.parse(
    """
    input{
      data_filename = None
        .type = path
        .help = "HDF5 data file"
    }
    """
)

tristan_scope = freephil.parse()

# Parse command line arguments
parser = argparse.ArgumentParser(
    description="Copy metadata from input NeXus file.",
    parents=[version_parser],
)

parser.add_argument("--debug", action="store_const", const=True)
parser.add_argument(
    "-c",
    "--show-config",
    action="store_true",
    default=False,
    dest="show_config",
    help="Show the configuration parameters.",
)

# CLIs
def copy_nexus(args):
    clai = general_scope.command_line_argument_interpreter()
    working_phil = general_scope.fetch(clai.process_and_fetch(args.phil_args))
    params = working_phil.extract()
    working_phil.show()
    print(params)


def copy_tristan_nexus(args):
    clai = tristan_scope.command_line_argument_interpreter()
    working_phil = tristan_scope.fetch(clai.process_and_fetch(args.phil_args))
    params = working_phil.extract()
    working_phil.show()
    print(params)


# Define subparsers
subparsers = parser.add_subparsers(
    help="Choose copy methods.",
    required=True,
    dest="sub-command",
)

parser_general = subparsers.add_parser(
    "gen",
    aliases=["copy-file"],
    description=("Copy experiment metadata to a new NeXus file."),
    parents=[full_copy_parser],
)
parser_general.set_defaults(func=copy_nexus)

parser_tristan = subparsers.add_parser(
    "tristan",
    aliases=["copy-tristan"],
    description=(
        "Create a new NeXus file for binned images by copying the metadata from the original experiment NeXus file."
    ),
    parents=[tristan_copy_parser],
)
parser_tristan.set_defaults(func=copy_tristan_nexus)


def main():
    # Define a stream handler
    CH = logging.StreamHandler(sys.stdout)
    CH.setLevel(logging.DEBUG)
    CH.setFormatter(formatter)
    # Add handler to logger
    logger.addHandler(CH)

    args = parser.parse_args()
    args.func(args)


main()
