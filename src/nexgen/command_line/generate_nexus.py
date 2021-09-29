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

    # Log information
    logger.info("Source information")
    logger.info(f"Facility: {source.name} - {source.type}.")
    logger.info(f"Beamline: {source.beamline_name}")

    if timestamps[0] is not None:
        logger.info(f"Collection start time: {timestamps[0]}")
    else:
        logger.warning("No collection start time recorded.")
    if timestamps[1] is not None:
        logger.info(f"Collection end time: {timestamps[1]}")
    else:
        logger.warning("No collection end time recorded.")

    logger.info("Coordinate system: %s" % cf)
    if cf == "imgcif":
        logger.warning(
            "Input coordinate frame is imgcif. They will be converted to mcstas."
        )

    logger.info("Goniometer information")
    axes = goniometer.axes
    axis_vectors = goniometer.vectors

    assert len(axis_vectors) == 3 * len(
        axes
    ), "Number of vectors does not match number of goniometer axes."

    for j in reversed(range(len(axes))):
        vector = axis_vectors[3 * j : 3 * j + 3]
        logger.info(
            f"Goniometer axis: {axes[j]} => {vector} ({goniometer.types[j]}) on {goniometer.depends[j]}. {goniometer.starts[j]} {goniometer.ends[j]} {goniometer.increments[j]}"
        )

    logger.info("")

    logger.info("Detector information:\n%s" % detector.description)
    logger.info(
        f"Sensor made of {detector.sensor_material} x {detector.sensor_thickness}mm"
    )
    logger.info(f"Trusted pixels > {detector.underload} and < {detector.overload}")
    logger.info(
        f"Image is a {detector.image_size} array of {detector.pixel_size} mm pixels"
    )

    logger.info("Detector axes:")
    axes = detector.axes
    axis_vectors = detector.vectors

    assert len(axis_vectors) == 3 * len(
        axes
    ), "Number of vectors does not match number of detector axes."

    for j in range(len(axes)):
        vector = axis_vectors[3 * j : 3 * j + 3]
        logger.info(
            f"Detector axis: {axes[j]} => {vector} ({detector.types[j]}) on {detector.depends[j]}. {detector.starts[j]}"
        )

    if detector.flatfield is None:
        logger.info("No flatfield applied")
    else:
        logger.info(f"Flatfield correction data lives here {detector.flatfield}")

    if detector.pixel_mask is None:
        logger.info("No bad pixel mask for this detector")
    else:
        logger.info(f"Bad pixel mask lives here {detector.pixel_mask}")

    logger.info("Module information")
    logger.info(f"Number of modules: {module.num_modules}")
    logger.info(f"Fast axis at datum position: {module.fast_axis}")
    logger.info(f"Slow_axis at datum position: {module.slow_axis}")
    if module.module_offset == "0":
        logger.warning(f"module_offset field will not be written.")
    logger.info("")

    logger.info("Start writing NeXus file ...")
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
        logger.info(f"{master_file} correctly written.")
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.error(err)

    logger.info("==" * 50)


main()
