"""
Command line tool to copy experiment metadata from one NeXus file to the other.
"""

import sys
import logging
import argparse
import freephil

from pathlib import Path

from . import (
    version_parser,
    full_copy_parser,
    tristan_copy_parser,
)

from ..nxs_copy import CopyNexus, CopyTristanNexus

# Define a logger object and a formatter
logger = logging.getLogger("CopyNeXus")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s %(message)s")

# Phil scopes
general_scope = freephil.parse(
    """
    input{
      original_nexus = None
        .type = path
        .help = "NeXus file to be copied."
      data_filename = None
        .multiple = True
        .type = path
        .help = "HDF5 data file."
      data_type = *images events
        .type = choice
        .help = "Type of data in the HDF5 file, can be either images or events."
      simple_copy = False
        .type = bool
        .help = "If True, the full NeXus tree is copied."
      skip = NXdata
        .multiple = True
        .optional = True
        .type = str
        .help = "NX_class object, or list of, to be skipped when copying metadata.
                If called, it will always first skip NXdata."
    }
    """
)

tristan_scope = freephil.parse(
    """
    input {
      tristan_nexus = None
        .type = path
        .help = "NeXus file associated with Tristan detector"
      data_filename = None
        .multiple = True
        .type = path
        .help = "HDF5 file with binned images"
      experiment_type = stationary *rotation
        .type = choice
        .help = "Specify whether an experiment is stationary or a rotation scan. Defaults to rotation."
      write_mode = r+ w *x a
        .type = choice
        .help = "Specify write mode for new NeXus file."
    }
    """
)

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

    logger.info("Copy metadata from one NeXus file to another.")

    # Path to data file and original nexus file
    data_file = [Path(d).expanduser().resolve() for d in params.input.data_filename]
    nexus_file = Path(params.input.original_nexus).expanduser().resolve()
    logger.info(f"NeXus file to be copied: {nexus_file}")
    logger.info(f"Input data to be saved in NeXus file: {data_file}")

    logger.info(f"Data type: {params.input.data_type}")
    if params.input.simple_copy is True:
        logger.info(f"{nexus_file} will be copied in its entirety.")
    else:
        logger.info(
            f"The following groups will not be copied from NXentry of {nexus_file}: {params.input.skip}"
        )
    try:
        if params.input.data_type == "images":
            new_nxs = CopyNexus.images_nexus(
                data_file,
                nexus_file,
                simple_copy=params.input.simple_copy,
                skip_group=params.input.skip,
            )
        elif params.input.data_type == "events":
            new_nxs = CopyNexus.pseudo_events_nexus(
                data_file,
                nexus_file,
            )
        logger.info(f"File {nexus_file} correctly copied to {new_nxs}.")
    except Exception as err:
        logger.info(f"File {nexus_file} could not be copied.")
        logger.exception(err)


def copy_tristan_nexus(args):
    clai = tristan_scope.command_line_argument_interpreter()
    working_phil = tristan_scope.fetch(clai.process_and_fetch(args.phil_args))
    params = working_phil.extract()
    working_phil.show()

    logger.info("Copy metadata from Tristan NeXus file.")

    # Path to data and original nexus file
    data_file = [Path(d).expanduser().resolve() for d in params.input.data_filename]
    nexus_file = Path(params.input.tristan_nexus).expanduser().resolve()
    logger.info(f"Working directory: {data_file[0].parent}")
    logger.info(f"NeXus file to be copied: {nexus_file}")
    logger.info(f"Input data to be saved in NeXus file: {data_file}")

    try:
        if params.input.experiment_type == "stationary":
            logger.info(
                "Copying metadata for a stationary dataset. \n"
                "This means either a single image or a pump-probe experiment.\n"
                "The 'scan_axis' will be a single scalar."
            )
            nxs_img = CopyTristanNexus.single_image_nexus(
                data_file[0],
                nexus_file,
                params.input.write_mode,
            )
        elif params.input.experiment_type == "rotation":
            logger.info(
                "Copying metadata for a roation dataset. \n"
                "This means either a multiple images or a multi sequences pump-probe experiment.\n"
            )
            if args.osc_angle:
                logger.info(
                    f"Scan_axis will be a list of values defined by an oscillation angle of {args.osc_angle}."
                )
            elif args.num_bins:
                logger.info(f"Scan_ axis will be a list of {args.num_bins} values.")

            for filename in data_file:
                nxs_img = CopyTristanNexus.multiple_images_nexus(
                    filename,
                    nexus_file,
                    params.input.write_mode,
                    args.osc_angle,
                    args.num_bins,
                )
        logger.info(
            f"Experiment metadata correctly copied from {nexus_file} to {nxs_img}."
        )
    except Exception as err:
        logger.info(f"File {nexus_file} could not be copied.")
        logger.exception(err)


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


# main()
