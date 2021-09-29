"""
Command line tool to generate a NeXus file.
"""

import sys
import h5py
import logging
import argparse

import freephil

from pathlib import Path

from __init__ import version_parser
from nexgen import get_nexus_filename, get_iso_timestamp
from nexgen.nxs_write.NexusWriter import write_nexus

# from . import version_parser
# from .. import get_nexus_filename, get_iso_timestamp
# from ..nxs_write.NexusWriter import write_nexus

# Define a logger object and a formatter
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(message)s")

master_phil = freephil.parse(
    """
    input {
      datafile = None
        .multiple = True
        .type = path
        .help = "HDF5 file. For now, assumes pattern filename_%0{6}d.h5"
      coordinate_frame = *mcstas imgcif
        .type = choice
        .help = "Which coordinate system is being used to provide input vectors."
      vds_writer = False
        .type = bool
        .help = "If True, write vds along with external link to data in NeXus file."
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
    description="Generate a NeXus file for data collection.",
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
parser.add_argument("phil_args", nargs="*")


def main():
    args = parser.parse_args()
    cl = master_phil.command_line_argument_interpreter()
    working_phil = master_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    # Path to data file
    datafiles = [Path(d).expanduser().resolve() for d in params.input.datafile]

    # Get NeXus file name
    master_file = get_nexus_filename(datafiles[0])

    # Start logger
    logfile = datafiles[0].parent / "generate_nexus_file.log"  # "NeXusWriter.log"
    # Define stream and file handler for logging
    CH = logging.StreamHandler(sys.stdout)
    CH.setLevel(logging.DEBUG)
    CH.setFormatter(formatter)
    FH = logging.FileHandler(logfile, mode="a")
    FH.setLevel(logging.DEBUG)
    FH.setFormatter(formatter)
    # Add handlers to logger
    logger.addHandler(CH)
    logger.addHandler(FH)

    # Add some information to logger
    logger.info("Create a NeXus file for %s" % datafiles)
    logger.info("NeXus file will be saved as %s" % master_file)

    # Load technical info from phil parser
    cf = params.input.coordinate_frame
    goniometer = params.goniometer
    detector = params.detector
    module = params.detector_module
    source = params.source
    beam = params.beam
    attenuator = params.attenuator
    timestamps = (
        get_iso_timestamp(params.start_time),
        get_iso_timestamp(params.end_time),
    )

    # TODO finish adding logging

    try:
        with h5py.File(master_file, "x") as nxsfile:
            write_nexus(
                nxsfile,
                datafiles,
                goniometer,
                detector,
                module,
                source,
                beam,
                attenuator,
                timestamps,
                cf,
            )
            # FIXME need to finish filling this one out!
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.error(err)

    logger.info("==" * 50)


main()
