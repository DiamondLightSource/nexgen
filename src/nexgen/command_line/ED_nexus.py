"""
Command line tool to generate NXmx-like NeXus files for Electron Diffraction.
"""

import argparse
import glob
import logging
import sys
from pathlib import Path

import freephil
import h5py

from .. import get_iso_timestamp, get_nexus_filename, log
from ..beamlines.ED_params import ED_coord_system
from ..nxs_write.EDNexusWriter import ED_call_writers
from ..tools.ED_tools import extract_from_SINGLA_master
from ..tools.VDS_tools import image_vds_writer, vds_file_writer
from . import config_parser, nexus_parser, phil2dict, version_parser

logger = logging.getLogger("nexgen.EDNeXusGenerator")

ED_phil = freephil.parse(
    """
    input {
      datafiles = None
        .type = path
        .help = "List of input data files."
      coordinate_frame = mcstas
        .type = str
        .help = "Which coordinate system is being used to provide input vectors."
      vds_writer = None *dataset file
        .type = choice
        .help = "If not None, write vds along with external link to data in NeXus file, or create _vds.h5 file."
      n_imgs = None
        .type = int
        .help = "Total number of images collected."
    }

    include scope nexgen.command_line.nxs_phil.goniometer_scope

    include scope nexgen.command_line.nxs_phil.beamline_scope

    include scope nexgen.command_line.nxs_phil.detector_scope

    include scope nexgen.command_line.nxs_phil.module_scope

    include scope nexgen.command_line.nxs_phil.timestamp_scope

    include scope nexgen.command_line.nxs_phil.coord_system_scope
    """,
    process_includes=True,
)

parser = argparse.ArgumentParser(description=__doc__, parents=[version_parser])
parser.add_argument("--debug", action="store_const", const=True)


def write_from_SINGLA(args):
    cl = ED_phil.command_line_argument_interpreter()
    working_phil = ED_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    if args.show_config:
        working_phil.show(attributes_level=args.attributes_level)
        sys.exit()

    datafiles = [
        Path(f).expanduser().resolve()
        for f in sorted(glob.glob(params.input.datafiles))
    ]

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

    # Load technical info from phil parser
    coordinate_frame = params.input.coordinate_frame
    # ED_coord_system = phil2dict(params.coord_system.__dict__)
    goniometer = phil2dict(params.goniometer.__dict__)
    detector = phil2dict(params.detector.__dict__)
    module = phil2dict(params.detector_module.__dict__)
    source = phil2dict(params.source.__dict__)
    beam = phil2dict(params.beam.__dict__)
    timestamps = (
        get_iso_timestamp(params.start_time),
        get_iso_timestamp(params.end_time),
    )

    logger.warning(
        f"Coordinate frame of input arrays currently set to {coordinate_frame}."
        "If that is not the case, please indicate the correct one with --coord-frame."
        "For more information, see the help message."
    )

    logger.warning(
        "Have you checked the coordinate system convention?\n"
        "If no new values have been passed for coord_system.origin or coord_system.vectors the following convention will be applied:\n"
        f"{ED_coord_system}"
    )

    # If anything has been passed regarding the new coordinate system convention
    # overwrite the existing dictionary
    if params.coord_system.convention:
        logger.info(
            f"New coordinate system convention: {params.coord_system.convention}."
        )
        ED_coord_system["convention"] = params.coord_system.convention

    if params.coord_system.origin:
        logger.info(
            f"New value for coordinate system found: {params.coord_system.origin}."
        )
        ED_coord_system["origin"] = tuple(params.coord_system.origin)

    if params.coord_system.vectors:
        from .. import split_arrays

        # Note: setting to coordinate frame to avoid any conversions. FIXME
        vectors = split_arrays(["x", "y", "z"], params.coord_system.vectors)
        logger.info(
            f"New vectors defined for {params.coord_system.convention} coordinate system."
        )
        ED_coord_system["x"] = (".", "translation", "mm", vectors["x"])
        ED_coord_system["y"] = ("x", "translation", "mm", vectors["y"])
        ED_coord_system["z"] = ("y", "translation", "mm", vectors["z"])

    if args.master:
        master = Path(args.master).expanduser().resolve()
        logger.info(
            f"Looking through Dectris master file to extract at least mask and flatfield."
        )
        detector.update(extract_from_SINGLA_master(master))

    # Start writing
    logger.info("Start writing NeXus file ...")
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
                n_images=params.input.n_imgs,
                timestamps=timestamps,
            )

            if params.input.vds_writer == "dataset":
                nimages = (
                    nxs["/entry/instrument/detector/detectorSpecific/nimages"][()]
                    if params.input.n_imgs is None
                    else params.input.n_imgs
                )
                logger.info("Calling VDS writer ...")
                image_vds_writer(
                    nxs,
                    (int(nimages), *detector["image_size"]),
                    entry_key="/entry/data/data",
                )
            elif params.input.vds_writer == "file":
                nimages = (
                    nxs["/entry/instrument/detector/detectorSpecific/nimages"][()]
                    if params.input.n_imgs is None
                    else params.input.n_imgs
                )
                logger.info(
                    "Calling VDS writer to write a Virtual Dataset file and relative link."
                )
                vds_file_writer(nxs, datafiles, (int(nimages), *detector["image_size"]))
            else:
                logger.info("VDS won't be written.")

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
    parents=[nexus_parser, config_parser],
)
# singla_parser.add_argument("datafiles", type=str, nargs="*", help="Image files.")
singla_parser.add_argument(
    "-m",
    "--master",
    type=str,
    help="HDF5 master file written by Singla detector.",
)
singla_parser.set_defaults(func=write_from_SINGLA)


def main():
    args = parser.parse_args()
    args.func(args)
