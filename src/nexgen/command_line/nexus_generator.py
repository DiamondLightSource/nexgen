"""
Command line tool to generate NeXus files.
"""

import argparse
import glob
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import freephil
import h5py
import numpy as np

from .. import log
from ..tools.data_writer import generate_event_files, generate_image_files
from ..tools.meta_reader import overwrite_beam, overwrite_detector
from ..utils import (
    get_filename_template,
    get_iso_timestamp,
    get_nexus_filename,
    units_of_time,
)
from . import (
    config_parser,
    demo_parser,
    detectormode_parser,
    nexus_parser,
    version_parser,
)
from .cli_utils import add_tristan_spec, call_writers, phil2dict

# Define a logger object
logger = logging.getLogger("nexgen.NeXusGenerator")

# Phil scopes
master_phil = freephil.parse(
    """
    output {
      master_filename = None
        .type = path
        .help = "Filename for master file"
    }
    input {
      datafile = None
        .type = path
        .help = "HDF5 file. For now, assumes pattern filename_%0{6}d.h5"
      coordinate_frame = *mcstas imgcif
        .type = choice
        .help = "Which coordinate system is being used to provide input vectors."
      vds_writer = None *dataset file
        .type = choice
        .help = "If not None, write vds along with external link to data in NeXus file, or create _vds.h5 file."
      snaked = False
        .type = bool
        .help = "Grid scan parameter. If True, the writer will draw a snaked grid."
    }

    include scope nexgen.command_line.nxs_phil.goniometer_scope

    include scope nexgen.command_line.nxs_phil.instrument_scope

    include scope nexgen.command_line.nxs_phil.detector_scope

    include scope nexgen.command_line.nxs_phil.module_scope

    include scope nexgen.command_line.nxs_phil.timestamp_scope
    """,
    process_includes=True,
)

demo_phil = freephil.parse(
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
      vds_writer = None *dataset file
        .type = choice
        .help = "If not None, either write a vds in the nexus file or create also a _vds.h5 file."
      snaked = False
        .type = bool
        .help = "Grid scan parameter. If True, the writer will draw a snaked grid."
    }

    include scope nexgen.command_line.nxs_phil.goniometer_scope

    include scope nexgen.command_line.nxs_phil.instrument_scope

    include scope nexgen.command_line.nxs_phil.detector_scope

    include scope nexgen.command_line.nxs_phil.module_scope
    """,
    process_includes=True,
)

meta_phil = freephil.parse(
    """
    output {
      master_filename = None
        .type = path
        .help = "Filename for master file"
    }
    input {
      metafile = None
        .type = path
        .help = "Path to _meta.h5 file for collection."
      datafile = None
        .type = path
        .help = "HDF5 file. For now, assumes pattern filename_%0{6}d.h5"
      coordinate_frame = *mcstas imgcif
        .type = choice
        .help = "Which coordinate system is being used to provide input vectors."
      vds_writer = None *dataset file
        .type = choice
        .help = "If not None, write vds along with external link to data in NeXus file, or create _vds.h5 file."
      snaked = False
        .type = bool
        .help = "Grid scan parameter. If True, the writer will draw a snaked grid."
    }

    include scope nexgen.command_line.nxs_phil.goniometer_scope

    include scope nexgen.command_line.nxs_phil.instrument_scope

    include scope nexgen.command_line.nxs_phil.detector_scope

    include scope nexgen.command_line.nxs_phil.module_scope

    include scope nexgen.command_line.nxs_phil.timestamp_scope
    """,
    process_includes=True,
)

# Parse command line arguments
parser = argparse.ArgumentParser(
    description="Generate a new NeXus file for data collection.",
    parents=[version_parser],
)
parser.add_argument("--debug", action="store_const", const=True)


# CLIs
def write_NXmx_cli(args):
    cl = master_phil.command_line_argument_interpreter()
    working_phil = master_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    if args.show_config:
        working_phil.show(attributes_level=args.attributes_level)
        sys.exit()

    # Path to data file
    datafiles = [
        Path(d).expanduser().resolve() for d in glob.glob(params.input.datafile)
    ]

    # Get NeXus file name
    if params.output.master_filename:
        master_file = Path(params.output.master_filename).expanduser().resolve()
    else:
        master_file = get_nexus_filename(datafiles[0])

    # Start logger
    logfile = master_file.parent / "generate_nexus.log"
    # Configure logging
    log.config(logfile.as_posix())

    logger.info("NeXus file writer for existing dataset.")

    # Add some information to logger
    logger.info("Create a NeXus file for %s" % datafiles[0])
    logger.info(
        "Number of experiment data files in directory, linked to the Nexus file: %d"
        % len(datafiles)
    )
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

    # If dealing with a tristan detector, add its specifications to detector scope.
    if "TRISTAN" in detector.description.upper():
        add_tristan_spec(detector, params.tristanSpec)
        logger.info("Tristan specs added to params for writing.")

    # Define images vs events based on detector mode
    logger.info(f"Data type: {detector.mode}.")
    if detector.mode == "events":
        data_type = ("events", None)
    else:
        if len(datafiles) == 1:
            with h5py.File(datafiles[0], "r") as f:
                num_images = f["data"].shape[0]
        else:
            from ..nxs_write.write_utils import find_number_of_images

            num_images = find_number_of_images(datafiles)
        data_type = ("images", num_images)
        logger.info(f"Total number of images: {num_images}")

    # Log information
    logger.info("Source information")
    logger.info(f"Facility: {source.name} - {source.type}.")
    logger.info(f"Beamline / Instrument: {source.beamline_name}")

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
    for tu in zip(goniometer.types, goniometer.units):
        assert tu in (
            ("translation", "mm"),
            ("rotation", "deg"),
        ), "Appropriate axis units should be: mm for translations, deg for rotations"

    assert len(axis_vectors) == 3 * len(
        axes
    ), "Number of vectors does not match number of goniometer axes."

    for j in reversed(range(len(axes))):
        vector = axis_vectors[3 * j : 3 * j + 3]
        logger.info(
            f"Goniometer axis: {axes[j]} => {vector} ({goniometer.types[j]}) on {goniometer.depends[j]}. {goniometer.starts[j]} {goniometer.ends[j]} {goniometer.increments[j]}"
        )

    logger.info("\n")

    logger.info(
        f"Detector information: {detector.description}, {detector.detector_type}"
    )
    logger.info(
        f"Sensor made of {detector.sensor_material} x {detector.sensor_thickness}"
    )
    logger.info(f"Trusted pixels > {detector.underload} and < {detector.overload}")
    logger.info(
        f"Image is a {detector.image_size[::-1]} array of {detector.pixel_size} pixels"
    )

    logger.info("Detector axes:")
    axes = detector.axes
    axis_vectors = detector.vectors
    for tu in zip(detector.types, detector.units):
        assert tu in (
            ("translation", "mm"),
            ("rotation", "deg"),
        ), "Appropriate axis units should be: mm for translations, deg for rotations"

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
        logger.warning("module_offset field will not be written.")
    logger.info("")

    if params.pump_probe.pump_status is True:
        logger.info("Pump probe status is True, write relative metadata as NXnote.")
        pump_info = {
            "pump_exposure_time": params.pump_probe.pump_exp,
            "pump_delay": params.pump_probe.pump_delay,
        }
    else:
        pump_info = None

    logger.info("Start writing NeXus file ...")
    try:
        call_writers(
            master_file,
            datafiles,
            cf,
            data_type,
            phil2dict(goniometer.__dict__),
            phil2dict(detector.__dict__),
            phil2dict(module.__dict__),
            phil2dict(source.__dict__),
            phil2dict(beam.__dict__),
            phil2dict(attenuator.__dict__),
            timestamps=timestamps,
            notes=pump_info,
        )
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.exception(err)

    logger.info("EOF\n")


def write_demo_cli(args):
    cl = demo_phil.command_line_argument_interpreter()
    working_phil = demo_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    if args.show_config:
        working_phil.show(attributes_level=args.attributes_level)
        sys.exit()

    # Path to file
    master_file = Path(params.output.master_filename).expanduser().resolve()
    # Just in case ...
    if master_file.suffix == ".h5" and "master" not in master_file.stem:
        master_file = Path(master_file.as_posix().replace(".h5", "_master.h5"))

    # Start logger
    logfile = master_file.parent / "generate_demo.log"
    # Configure logging
    log.config(logfile.as_posix())

    logger.info("Demo NeXus file writer with blank data HDF5 files.")

    # Get data file name template
    data_file_template = get_filename_template(master_file)

    # Add some information to logger
    logger.info("NeXus file will be saved as %s" % params.output.master_filename)
    logger.info("Data file(s) template: %s" % data_file_template)

    # Next: go through technical info (goniometer, detector, beamline etc ...)
    cf = params.input.coordinate_frame
    goniometer = params.goniometer
    detector = params.detector
    module = params.detector_module
    source = params.source
    beam = params.beam
    attenuator = params.attenuator

    # If dealing with a tristan detector, add its specifications to detector scope.
    if "TRISTAN" in detector.description.upper():
        add_tristan_spec(detector, params.tristanSpec)

    # Images or events ?
    if args.events is True:
        num_events = args.force if args.force else 1
        data_type = ("events", num_events)
    else:
        num_images = args.force if args.force else None
        data_type = ("images", num_images)

    # Log information
    logger.info("Data type: %s" % data_type[0])

    logger.info("Source information")
    logger.info(f"Facility: {source.name} - {source.type}.")
    logger.info(f"Beamline / Instrument: {source.beamline_name}")

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

    assert len(axis_vectors) == 3 * len(
        axes
    ), "Number of vectors does not match number of axes."

    for j in reversed(range(len(axes))):
        vector = axis_vectors[3 * j : 3 * j + 3]
        logger.info(
            f"Goniometer axis: {axes[j]} => {vector} ({goniometer.types[j]}) on {goniometer.depends[j]}. {goniometer.starts[j]} {goniometer.ends[j]} {goniometer.increments[j]}"
        )

    logger.info("")

    # Fix the number of images if not passed from command line.
    if data_type[0] == "images" and data_type[1] is None:
        raise ValueError("Missing number of images. Please specify how many to write.")

    logger.info("Detector information: %s" % detector.description)
    logger.info(
        f"Sensor made of {detector.sensor_material} x {detector.sensor_thickness}"
    )
    if data_type[0] == "images":
        logger.info(f"Trusted pixels > {detector.underload} and < {detector.overload}")
    logger.info(
        f"Image is a {detector.image_size[::-1]} array of {detector.pixel_size} pixels"
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

    # Figure out how many files will need to be written
    logger.info("Calculating number of files to write ...")
    if data_type[0] == "events":
        # Determine the number of files. Write one file per module.
        # FIXME Either a 10M or a 2M, no other possibilities at this moment.
        n_files = 10 if "10M" in detector.description.upper() else 2
    else:
        # The maximum number of images being written each dataset is 1000
        if data_type[1] <= 1000:
            n_files = 1
        else:
            n_files = int(np.ceil(data_type[1] / 1000))

    logger.info("%d file(s) containing blank data to be written." % n_files)

    # Get datafile list
    datafiles = [
        Path(data_file_template % (n + 1)).expanduser().resolve()
        for n in range(n_files)
    ]

    logger.info("Calling data writer ...")
    # Write data files
    if data_type[0] == "images":
        generate_image_files(
            datafiles, detector.image_size, detector.description, data_type[1]
        )
    else:
        exp_time = units_of_time(detector.exposure_time)
        generate_event_files(
            datafiles, data_type[1], detector.description, exp_time.magnitude
        )

    logger.info("\n")

    # Record string with start_time
    start_time = datetime.fromtimestamp(time.time()).strftime("%A, %d. %B %Y %I:%M%p")

    if params.pump_probe.pump_status is True:
        logger.info("Pump probe status is True, write relative metadata as NXnote.")
        pump_info = {
            "pump_exposure_time": params.pump_probe.pump_exp,
            "pump_delay": params.pump_probe.pump_delay,
        }
    else:
        pump_info = None

    # Record string with end_time
    end_time = datetime.fromtimestamp(time.time()).strftime("%A, %d. %B %Y %I:%M%p")

    # Write /entry/start_time and /entry/end_time
    timestamps = (get_iso_timestamp(start_time), get_iso_timestamp(end_time))
    logger.info("Start writing demo NXmx NeXus and data files ...")
    try:
        call_writers(
            master_file,
            datafiles,
            cf,
            data_type,
            phil2dict(goniometer.__dict__),
            phil2dict(detector.__dict__),
            phil2dict(module.__dict__),
            phil2dict(source.__dict__),
            phil2dict(beam.__dict__),
            phil2dict(attenuator.__dict__),
            timestamps=timestamps,
            notes=pump_info,
        )
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.exception(err)

    logger.info("EOF\n")


def write_with_meta_cli(args):
    cl = meta_phil.command_line_argument_interpreter()
    working_phil = meta_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    if args.show_config:
        working_phil.show(attributes_level=args.attributes_level)
        sys.exit()

    # Path to meta file
    if params.input.metafile:
        metafile = Path(params.input.metafile).expanduser().resolve()
    else:
        sys.exit(
            "Please pass a _meta.h5 file. If not available use 'nexus' option instead."
        )

    # Get NeXus filename
    if params.output.master_filename:
        master_file = Path(params.output.master_filename).expanduser().resolve()
    else:
        master_file = get_nexus_filename(metafile)

    # If no datafile has been passed, look for them in the directory
    if params.input.datafile:
        datafiles = [
            Path(d).expanduser().resolve() for d in glob.glob(params.input.datafile)
        ]
    else:
        datafile_pattern = (
            metafile.parent / f"{master_file.stem}_{6*'[0-9]'}.h5"
        ).as_posix()
        datafiles = [
            Path(d).expanduser().resolve() for d in sorted(glob.glob(datafile_pattern))
        ]

    # Start logger
    logfile = master_file.parent / "generate_nexus_from_meta.log"
    # Configure logging
    log.config(logfile.as_posix())

    logger.info("NeXus file writer for existing dataset with meta file available.")

    # Add some information to logger
    logger.info("Create a NeXus file for %s" % datafiles[0])
    logger.info(
        "Number of experiment data files in directory, linked to the Nexus file: %d"
        % len(datafiles)
    )
    logger.info("Meta file for the collection: %s" % metafile)
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

    # If dealing with a tristan detector, add its specifications to detector scope.
    if "TRISTAN" in detector.description.upper():
        add_tristan_spec(detector, params.tristanSpec)

    # Define images vs events based on detector mode
    logger.info(f"Data type: {detector.mode}.")
    if detector.mode == "events":
        data_type = ("events", None)
    else:
        if len(datafiles) == 1:
            with h5py.File(datafiles[0], "r") as f:
                num_images = f["data"].shape[0]
        else:
            from ..nxs_write.write_utils import find_number_of_images

            num_images = find_number_of_images(datafiles)
        data_type = ("images", num_images)
        logger.info(f"Total number of images: {num_images}")

    # Log information
    logger.info("Source information")
    logger.info(f"Facility: {source.name} - {source.type}.")
    logger.info(f"Beamline / Instrument: {source.beamline_name}")

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
    for tu in zip(goniometer.types, goniometer.units):
        assert tu in (
            ("translation", "mm"),
            ("rotation", "deg"),
        ), "Appropriate axis units should be: mm for translations, deg for rotations"

    assert len(axis_vectors) == 3 * len(
        axes
    ), "Number of vectors does not match number of goniometer axes."

    for j in reversed(range(len(axes))):
        vector = axis_vectors[3 * j : 3 * j + 3]
        logger.info(
            f"Goniometer axis: {axes[j]} => {vector} ({goniometer.types[j]}) on {goniometer.depends[j]}. {goniometer.starts[j]} {goniometer.ends[j]} {goniometer.increments[j]}"
        )

    logger.info("\n")

    if detector.description is None:
        logger.error("No detector description provided, exit.")
        raise ValueError("Please provide a detector description for identification.")

    logger.info(
        f"Detector information: {detector.description}, {detector.detector_type}"
    )
    logger.info(
        f"Sensor made of {detector.sensor_material} x {detector.sensor_thickness}"
    )
    logger.info(f"Trusted pixels > {detector.underload} and < {detector.overload}")
    logger.info(
        f"Image is a {detector.image_size[::-1]} array of {detector.pixel_size} pixels"
    )

    logger.info("Detector axes:")
    axes = detector.axes
    axis_vectors = detector.vectors
    for tu in zip(detector.types, detector.units):
        assert tu in (
            ("translation", "mm"),
            ("rotation", "deg"),
        ), "Appropriate axis units should be: mm for translations, deg for rotations"

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
        logger.warning("module_offset field will not be written.")
    logger.info("")

    if args.no_ow:
        logger.warning(f"The following datasets will not be overwritten: {args.no_ow}")
        ignore = args.no_ow
    else:
        ignore = None

    logger.info("Looking through _meta.h5 file for metadata.")

    with h5py.File(metafile, "r", libver="latest", swmr=True) as mf:
        overwrite_beam(mf, detector.description, beam)
        _ = overwrite_detector(mf, detector, ignore)

    logger.info("Start writing NeXus file ...")

    if params.pump_probe.pump_status is True:
        logger.info("Pump probe status is True, write relative metadata as NXnote.")
        pump_info = {
            "pump_exposure_time": params.pump_probe.pump_exp,
            "pump_delay": params.pump_probe.pump_delay,
        }
    else:
        pump_info = None

    try:
        call_writers(
            master_file,
            datafiles,
            cf,
            data_type,
            phil2dict(goniometer.__dict__),
            phil2dict(detector.__dict__),
            phil2dict(module.__dict__),
            phil2dict(source.__dict__),
            phil2dict(beam.__dict__),
            phil2dict(attenuator.__dict__),
            metafile=True,
            timestamps=timestamps,
            notes=pump_info,
        )
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.exception(err)

    logger.info("EOF\n")


# Define subparsers
subparsers = parser.add_subparsers(
    help="Choose whether to write a NXmx NeXus file for a collection or a demo. \
        Run generate_nexus <command> --help to see the parameters for each sub-command.",
    required=True,
    dest="sub-command",
)

parser_NXmx = subparsers.add_parser(
    "1",
    aliases=["nexus"],
    description=("Trigger NeXus file writing pointing to existing data."),
    parents=[nexus_parser, config_parser],
)
parser_NXmx.set_defaults(func=write_NXmx_cli)

parser_NXmx_demo = subparsers.add_parser(
    "2",
    aliases=["demo"],
    description=(
        "Trigger NeXus and blank data file writing. "
        "This option always requires either the -i or -e flags, which are mutually exclusive arguments."
    ),
    parents=[demo_parser, detectormode_parser, config_parser],
)
parser_NXmx_demo.set_defaults(func=write_demo_cli)

parser_NXmx_meta = subparsers.add_parser(
    "3",
    aliases=["meta"],
    description=(
        "Trigger NeXus file writing pointing to an existing collection with a meta file."
    ),
    parents=[nexus_parser, config_parser],
)
parser_NXmx_meta.add_argument(
    "-no",
    "--no_ow",
    nargs="+",
    help="List of datasets that should not be overwritten even if present in meta file",
    type=str,
)
parser_NXmx_meta.set_defaults(func=write_with_meta_cli)


def main():
    args = parser.parse_args()
    args.func(args)


# main()
