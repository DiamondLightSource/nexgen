"""
Command line tool to generate NXmx-like NeXus files for Electron Diffraction.
"""

import argparse
import logging
from pathlib import Path

import h5py

from nexgen.nxs_write import find_number_of_images

from .. import get_iso_timestamp, get_nexus_filename, log
from ..beamlines.ED_params import ED_coord_system, beam, goniometer, module, source
from ..nxs_write.EDNexusWriter import ED_call_writers
from ..tools.ED_tools import extract_from_SINGLA_master
from ..tools.VDS_tools import image_vds_writer
from . import EDcoord_parser, version_parser

logger = logging.getLogger("nexgen.EDNeXusGenerator")

parser = argparse.ArgumentParser(description=__doc__, parents=[version_parser])
parser.add_argument("--debug", action="store_const", const=True)
parser.add_argument("-start", type=str, help="Collection start time.")
parser.add_argument("-stop", type=str, help="Collection end time.")
parser.add_argument("-vds", action="store_true", default=False)


def write_from_SINGLA(args):
    from ..beamlines.ED_params import singla_1M as detector

    datafiles = [Path(f).expanduser().resolve() for f in args.datafiles]

    # Configure logger
    logfile = datafiles[0].parent / "EDnxs.log"
    log.config(logfile.as_posix())

    # Get NeXus file name
    infile = datafiles[0].parent / datafiles[0].name.replace("_data", "")
    nxsfile = get_nexus_filename(infile)

    logger.info("NeXus file writer for electron diffraction data from Singla.")
    logger.info(
        "Number of experiment data files in directory, linked to the Nexus file: %d"
        % len(datafiles)
    )
    logger.info("NeXus file will be saved as %s" % nxsfile)

    if args.master:
        master = Path(args.master).expanduser().resolve()
        logger.info(
            f"Looking through Dectris master file to extract at least mask and flatfield."
        )
        detector.update(extract_from_SINGLA_master(master))

    coordinate_frame = args.coord_frame
    logger.warning(
        f"Coordinate frame of input arrays currently set to {coordinate_frame}."
        "If that is not the case, please indicate the correct one with --coord-frame."
        "For more information, see the help message."
    )
    # TODO Overwrite EDcoord dictionary if needed here

    start_time = get_iso_timestamp(args.start) if args.start else None
    end_time = get_iso_timestamp(args.stop) if args.stop else None

    # Add some logging here

    # Start writing
    try:
        with h5py.File(nxsfile, "x") as nxs:
            ED_call_writers(
                nxs,
                datafiles,
                goniometer,
                detector,
                module,
                source,
                beam,
                ED_coord_system,
                coordinate_frame=coordinate_frame,
                timestamps=(start_time, end_time),
            )

        if args.vds is True:
            nimages = find_number_of_images(datafiles, "/entry/data/data")
            image_vds_writer(nxs, (int(nimages), *detector["image_size"]))

        logger.info("NeXus file written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(f"An error occurred and {nxsfile} couldn't be written correctly.")


subparsers = parser.add_subparsers(
    help="Define what to do with input file depending on their origin.",
    required=True,
    dest="sub-command",
)

singla_parser = subparsers.add_parser(
    "singla",
    description=("Trigger NeXus file writing for Single data."),
    parents=[EDcoord_parser],
)
singla_parser.add_argument("datafiles", type=str, nargs="*", help="Image files.")
singla_parser.add_argument(
    "-master", type=str, help="HDF5 master file written by Singla detector."
)
singla_parser.set_defaults(func=write_from_SINGLA)


def main():
    args = parser.parse_args()
    args.func(args)
