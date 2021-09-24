"""
Command line tool to generate an example NeXus file along with blank data.
"""

import sys
import time
import h5py
import logging
import argparse

import numpy as np

from datetime import datetime
from pathlib import Path

import freephil

from __init__ import version_parser, detectormode_parser, _CheckFileExtension
from nexgen import get_filename_template

# from nexgen.nxs_write.__init__ import create_attributes
from nexgen.nxs_write.NexusWriter import write_new_example_nexus

# from . import version_parser, detectormode_parser, _CheckFileExtension
# from .. import get_filename_template
# from ..nxs_write import create_attributes
# from ..nxs_write.NexusWriter import write_new_nexus

# Define a logger object and a formatter
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(message)s")
# formatter = logging.Formatter("%(levelname)s %(message)s")

master_phil = freephil.parse(
    """
    output {
      master_filename = nexus_master.h5
        .type = path
        .help = "Filename for master file"
    }

    input {
      coordinate_frame = *mcstas imgcif
        .type = choice
        .help = "Which coordinate system is being used to provide input vectors"
      definition = NXmx
        .type = str
        .help = "Application definition for NeXus file. Deafults to Nxmx."
      n_files = 1
        .type = int
        .help = "Number of data files to write - defaults to 1."
      write_vds = False
        .type = bool
        .help = "If True, create also a _vds.h5 file. Only for image data."
    }

    include scope nexgen.command_line.nxs_phil.goniometer_scope

    include scope nexgen.command_line.nxs_phil.beamline_scope

    include scope nexgen.command_line.nxs_phil.detector_scope

    include scope nexgen.command_line.nxs_phil.module_scope
    """,
    process_includes=True,
)

# Parse command line arguments
parser = argparse.ArgumentParser(
    # description = __doc__,
    description="Parse parameters to generate a NeXus file.",
    parents=[version_parser, detectormode_parser],
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
# FIXME .multiple doesn't seem to work (not an argparse problem)
# Per forza non funziona, c'era impostato 3 come dimensione!!!
parser.add_argument("phil_args", nargs="*", action=_CheckFileExtension)


def main():
    args = parser.parse_args()
    cl = master_phil.command_line_argument_interpreter()
    working_phil = master_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    # Path to file
    master_file = Path(params.output.master_filename).expanduser().resolve()

    # Start logger
    logfile = master_file.parent / "NeXusWriter.log"
    # Define stream and file handler for logging
    CH = logging.StreamHandler(sys.stdout)
    CH.setLevel(logging.DEBUG)
    CH.setFormatter(formatter)
    FH = logging.FileHandler(logfile, mode="w")
    FH.setLevel(logging.DEBUG)
    FH.setFormatter(formatter)
    # Add handlers to logger
    logger.addHandler(CH)
    logger.addHandler(FH)

    # Just in case ...
    if master_file.suffix == ".h5" and "master" not in master_file.stem:
        master_file = Path(master_file.as_posix().replace(".h5", "_master.h5"))

    # Get data file name template
    data_file_template = get_filename_template(master_file)
    data_file_list = [
        Path(data_file_template % (n + 1)).expanduser().resolve()
        for n in range(params.input.n_files)
    ]
    # TODO add vds if prompted

    # Add some information to logger
    logger.info("NeXus file will be saved as %s" % params.output.master_filename)
    logger.info("Data file(s) template: %s" % data_file_template)
    logger.info(
        "%d file(s) containing blank data to be written." % params.input.n_files
    )

    # Next: go through technical info (goniometer, detector, beamline etc ...)
    if args.num_events:
        data_type = ("events", args.num_events)
    else:
        data_type = ("images", args.num_images)
    cf = params.input.coordinate_frame
    goniometer = params.goniometer
    detector = params.detector
    module = params.detector_module
    source = params.source
    beam = params.beam
    attenuator = params.attenuator

    # Log information
    logger.info("Data type: %s" % data_type[0])

    logger.info("Source information")
    logger.info(f"Facility: {source.name} - {source.type}.")
    logger.info(f"Beamline: {source.beamline_name}")

    logger.info("Coordinate system: %s" % cf)
    if cf == "imgcif":
        logger.warning(
            "Input coordinate frame is imgcif. They will be converted to mcstas."
        )

    logger.info("Goniometer information")
    axes = goniometer.axes
    axis_vectors = goniometer.vectors

    for tu in zip(goniometer.types, goniometer.units):
        assert tu in (("translation", "mm"), ("rotation", "deg"))

    assert len(axis_vectors) == 3 * len(axes)

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
    if data_type[0] == "images":
        logger.info(f"Trusted pixels > {detector.underload} and < {detector.overload}")
    logger.info(
        f"Image is a {detector.image_size} array of {detector.pixel_size} mm pixels"
    )

    logger.info("Detector axes:")
    axes = detector.axes
    axis_vectors = detector.vectors
    for tu in zip(detector.types, detector.units):
        assert tu in (("translation", "mm"), ("rotation", "deg"))

    assert len(axis_vectors) == 3 * len(axes)

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
    logger.warning(f"module_offset field setting: {module.module_offset}")
    logger.info(f"Number of modules: {module.num_modules}")
    logger.info(f"Fast axis at datum position: {module.fast_axis}")
    logger.info(f"Slow_axis at datum position: {module.slow_axis}")
    logger.info("")

    # Record string with start_time
    start_time = datetime.fromtimestamp(time.time()).strftime("%A, %d. %B %Y %I:%M%p")

    with h5py.File(master_file, "x") as nxsfile:
        # Set default attribute
        nxsfile.attrs["default"] = "entry"

        # Start writing the NeXus tree with NXentry at the top level
        nxentry = nxsfile.create_group("entry")
        nxentry.attrs["NX_class"] = "NXentry"
        nxentry.attrs["default"] = "data"
        # create_attributes(nxentry, ("NX_class", "default"), ("NXentry", "data"))

        # Application definition: entry/definition
        nxentry.create_dataset("definition", data=np.string_(params.input.definition))

        write_new_example_nexus(
            nxsfile,
            data_file_list,
            data_type,
            cf,
            goniometer,
            detector,
            module,
            source,
            beam,
            attenuator,
        )

        # Record string with end_time
        end_time = datetime.fromtimestamp(time.time()).strftime("%A, %d. %B %Y %I:%M%p")

        # Write /entry/start_time and /entry/end_time
        nxentry.create_dataset("start_time", data=np.string_(start_time))
        nxentry.create_dataset("end_time", data=np.string_(end_time))

    logger.info("==" * 50)


main()
