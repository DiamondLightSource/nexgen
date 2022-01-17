"""
Command line tool to get an existing .phil file with goniometer/detector metadata or to create a new one.
These files can be used as input for the NeXus generator CLI.
"""

import shutil
import argparse
import freephil

try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 compatibility
    from importlib_resources import files

from pathlib import Path

from . import version_parser, nexus_parser

from .. import beamlines

scopes = freephil.parse(
    """
    include scope nexgen.command_line.nxs_phil.goniometer_scope
    include scope nexgen.command_line.nxs_phil.beamline_scope
    include scope nexgen.command_line.nxs_phil.detector_scope
    include scope nexgen.command_line.nxs_phil.module_scope
    """,
    process_includes=True,
)

parser = argparse.ArgumentParser(description=__doc__, parents=[version_parser])
parser.add_argument("--debug", action="store_const", const=True)


def list_available_phil():
    filedir = files(beamlines)
    for f in filedir.glob("*.phil"):
        print(f.name)


def get_beamline_phil(args):
    # Determine where to save file
    if args.output:
        odir = Path(args.output).expanduser().resolve()
    else:
        odir = Path(".").expanduser().resolve()
        print(
            "No output directory was specified by user. A copy of the file will be saved in the current directory."
        )

    # Look for file
    filedir = files(beamlines)
    found = [f for f in sorted(filedir.glob("*.phil")) if args.phil_file == f.name]
    if len(found) == 0:
        print(f"No {args.phil_file} found.")
    elif len(found) == 1:
        print(f"{args.phil_file} found. Copying in {odir}.")
        shutil.copy(found[0], odir)


def create_new_phil(args):
    cl = scopes.command_line_argument_interpreter()
    working_phil = scopes.fetch(cl.process_and_fetch(args.phil_args))

    # Write to file
    if args.filename:
        filename = Path(args.filename).expanduser().resolve()
        with open(filename, "w") as fout:
            fout.write(working_phil.as_str())
    else:
        # working_phil.show()
        print(working_phil.as_str())


# Define subparsers
subparser = parser.add_subparsers(
    help="Run nexgen_phil <command> --help to see the options for each command.",
    required=True,
    dest="command",
)

parser_list = subparser.add_parser(
    "list",
    description=("Print out a list of currently available .phil template files."),
)
parser_list.set_defaults(func=list_available_phil)

parser_get = subparser.add_parser(
    "get",
    description=(
        "Get a copy of a .phil file to use as input for the NeXus file writer."
    ),
)
parser_get.add_argument("phil_file", type=str, help="Requested file name.")
parser_get.add_argument("-o", "--output", type=str, help="Specify output directory.")
parser_get.set_defaults(func=get_beamline_phil)

parser_create = subparser.add_parser(
    "new",
    description=("Write a new .phil file."),
    parents=[nexus_parser],
)
parser_create.add_argument(
    "-f", "--filename", type=str, help="Filename for new .phil template."
)
# parser_create.add_argument("phil_args", nargs="*")
parser_create.set_defaults(func=create_new_phil)


def main():
    args = parser.parse_args()
    if args.command == "list":
        args.func()
    else:
        args.func(args)


# main()
