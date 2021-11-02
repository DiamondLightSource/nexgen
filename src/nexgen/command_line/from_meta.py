"""
Generate a NeXus file using the information from the _meta.h5 file to override the phil scope.
"""

import sys

import glob
import h5py
import logging
import argparse
import freephil

from pathlib import Path

from . import (
    version_parser,
    nexus_parser,
)

from .. import (
    get_nexus_filename,
    # get_iso_timestamp,
)

# from ..nxs_write.NexusWriter import

# Define logger
logger = logging.getLogger("NeXusGenerator")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s %(message)s")

# Define phil scope
master_phil = freephil.parse(
    """
    input {
      meta_file = None
        .type = path
        .help = "Path to _meta.h5 file."
      datafile = None
        .multiple = True
        .type = path
        .help = "HDF5 file. For now, assumes pattern filename_%0{6}d.h5"
      coordinate_frame = *mcstas imgcif
        .type = choice
        .help = "Which coordinate system is being used to provide input vectors."
      vds_writer = *None dataset file
        .type = choice
        .help = "If not None, write vds along with external link to data in NeXus file, or create _vds.h5 file."
    }

    include scope nexgen.command_line.nxs_phil.goniometer_scope

    include scope nexgen.command_line.nxs_phil.beamline_scope

    include scope nexgen.command_line.nxs_phil.detector_scope

    include scope nexgen.command_line.nxs_phil.module_scope

    include scope nexgen.command_line.nxs_phil.timestamp_scope
    """,
    process_includes=True,
)

# Parse command line arguments
parser = argparse.ArgumentParser(
    description=__doc__,
    parents=[version_parser, nexus_parser],
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

# parser.add_argument(
#     "-ow",
#     "--overwrite",
#     action="store_true",
#     help="If there is a _meta.h5 file passed as input, override some detector parser information with values from it.",
# )

# CLI
def write_NXmx_from_meta(args):
    cl = master_phil.command_line_argument_interpreter()
    working_phil = master_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    # Path to meta file
    if params.input.meta_file:
        meta_file = Path(params.input.meta_file).expanduser().resolve()
    else:
        sys.exit(
            "Please pass a _meta.h5 file. If not available call generate_nexus instead."
        )

    # Get NeXus filename
    master_file = get_nexus_filename(meta_file)
    print(master_file)

    # If no datafile has been passed, look for them in the directory
    if params.input.datafile:
        datafiles = [Path(d).expanduser().resolve() for d in params.input.datafile]
    else:
        datafile_pattern = (
            meta_file.parent / f"{master_file.stem}_{6*'[0-9]'}.h5"
        ).as_posix()
        datafiles = [
            Path(d).expanduser().resolve() for d in sorted(glob.glob(datafile_pattern))
        ]

    # Start logger
    logfile = meta_file.parent / "generate_nexus_from_meta.log"
    # Define a file handler for logging
    FH = logging.FileHandler(logfile, mode="a")
    FH.setLevel(logging.DEBUG)
    FH.setFormatter(formatter)
    # Add handlers to logger
    logger.addHandler(FH)

    # Add some information to logger
    logger.info("Create a NeXus file for %s" % datafiles[0])
    logger.info(
        "Number of experiment data files in directory, linked to the Nexus file: %d"
        % len(datafiles)
    )
    logger.info("Meta file for the collection: %s" % meta_file)
    logger.info("NeXus file will be saved as %s" % master_file)

    # Load technical info from phil parser
    # cf = params.input.coordinate_frame
    # goniometer = params.goniometer
    # detector = params.detector
    # module = params.detector_module
    # source = params.source
    # beam = params.beam
    # attenuator = params.attenuator
    # timestamps = (
    #     get_iso_timestamp(params.start_time),
    #     get_iso_timestamp(params.end_time),
    # )

    # Detector definition HAS TO be passed.
    # That's the discriminant to decide what to look for in the meta file.

    try:
        with h5py.File(master_file, "x") as nxsfile:
            print(nxsfile)
            # TODO call writer here
            logger.info(f"{master_file} correctly written.")
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.exception(err)


# Main
def main():
    # Define a stram handler
    CH = logging.StreamHandler(sys.stdout)
    CH.setLevel(logging.DEBUG)
    CH.setFormatter(formatter)
    logger.addHandler(CH)

    # Parse arguments
    args = parser.parse_args()
    write_NXmx_from_meta(args)


main()
