"""
Command line tool to generate NeXus files.
"""

import sys
import glob
import h5py
import time
import logging
import argparse
import freephil

import numpy as np

from pathlib import Path
from datetime import datetime

from . import (
    version_parser,
    detectormode_parser,
    nexus_parser,
    demo_parser,
    add_tristan_spec,
)
from .. import (
    get_nexus_filename,
    get_filename_template,
    get_iso_timestamp,
    units_of_time,
)

# from ..nxs_write import (
#    find_osc_axis,
#    calculate_rotation_scan_range,
#    find_grid_scan_axes,
#    calculate_grid_scan_range,
# )
from ..nxs_write.NexusWriter import (
    write_nexus,
    call_writers,
    ScanReader,
)  # write_nexus_demo,
from ..nxs_write.NXclassWriters import write_NXnote, write_NXdatetime, write_NXentry
from ..tools.DataWriter import generate_image_files, generate_event_files
from ..tools.VDS_tools import image_vds_writer, vds_file_writer

# Define a logger object and a formatter
logger = logging.getLogger("NeXusGenerator")
logger.setLevel(logging.DEBUG)
# formatter = logging.Formatter("%(levelname)s %(message)s")
formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

# Phil scopes
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
      vds_writer = *None dataset file
        .type = choice
        .help = "If not None, either write a vds in the nexus file or create also a _vds.h5 file."
      snaked = False
        .type = bool
        .help = "Grid scan parameter. If True, the writer will draw a snaked grid."
    }

    include scope nexgen.command_line.nxs_phil.goniometer_scope

    include scope nexgen.command_line.nxs_phil.beamline_scope

    include scope nexgen.command_line.nxs_phil.detector_scope

    include scope nexgen.command_line.nxs_phil.module_scope
    """,
    process_includes=True,
)

meta_phil = freephil.parse(
    """
    input {
      metafile = None
        .type = path
        .help = "Path to _meta.h5 file for collection."
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

    # include scope nexgen.command_line.nexus_generator.master_phil
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

# CLIs
def write_NXmx_cli(args):
    cl = master_phil.command_line_argument_interpreter()
    working_phil = master_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    # Path to data file
    datafiles = [Path(d).expanduser().resolve() for d in params.input.datafile]

    # Get NeXus file name
    master_file = get_nexus_filename(datafiles[0])

    # Start logger
    logfile = datafiles[0].parent / "generate_nexus.log"
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
    for tu in zip(goniometer.types, goniometer.units):
        assert tu in (
            ("translation", "mm"),
            ("rotation", "deg"),
        ), "Appropriate axis units should be: mm for translations, det for rotations"

    assert len(axis_vectors) == 3 * len(
        axes
    ), "Number of vectors does not match number of goniometer axes."

    for j in reversed(range(len(axes))):
        vector = axis_vectors[3 * j : 3 * j + 3]
        logger.info(
            f"Goniometer axis: {axes[j]} => {vector} ({goniometer.types[j]}) on {goniometer.depends[j]}. {goniometer.starts[j]} {goniometer.ends[j]} {goniometer.increments[j]}"
        )

    logger.info("")

    logger.info(
        f"Detector information:\n {detector.description}, {detector.detector_type}"
    )
    logger.info(
        f"Sensor made of {detector.sensor_material} x {detector.sensor_thickness}"
    )
    logger.info(f"Trusted pixels > {detector.underload} and < {detector.overload}")
    logger.info(
        f"Image is a {detector.image_size} array of {detector.pixel_size} pixels"
    )

    logger.info("Detector axes:")
    axes = detector.axes
    axis_vectors = detector.vectors
    for tu in zip(detector.types, detector.units):
        assert tu in (
            ("translation", "mm"),
            ("rotation", "deg"),
        ), "Appropriate axis units should be: mm for translations, det for rotations"

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
                params.input.vds_writer,
            )

            # Check and save pump status
            if params.pump_probe.pump_status is True:
                logger.info(
                    "Pump probe status is True, write relative metadata as NXnote."
                )
                pump_info = {
                    "pump_exposure_time": params.pump_probe.pump_exp,
                    "pump_delay": params.pump_probe.pump_delay,
                }
                write_NXnote(nxsfile, "/entry/source/notes", pump_info)

        logger.info(f"{master_file} correctly written.")
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.exception(err)
        # logger.error(err)

    logger.info("EOF")


def write_demo_cli(args):
    cl = demo_phil.command_line_argument_interpreter()
    working_phil = demo_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    # Path to file
    master_file = Path(params.output.master_filename).expanduser().resolve()
    # Just in case ...
    if master_file.suffix == ".h5" and "master" not in master_file.stem:
        master_file = Path(master_file.as_posix().replace(".h5", "_master.h5"))

    # Start logger
    logfile = master_file.parent / "generate_demo.log"
    # Define a file handler for logging
    FH = logging.FileHandler(logfile, mode="w")
    FH.setLevel(logging.DEBUG)
    FH.setFormatter(formatter)
    # Add handlers to logger
    logger.addHandler(FH)

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

    assert len(axis_vectors) == 3 * len(
        axes
    ), "Number of vectors does not match number of axes."

    for j in reversed(range(len(axes))):
        vector = axis_vectors[3 * j : 3 * j + 3]
        logger.info(
            f"Goniometer axis: {axes[j]} => {vector} ({goniometer.types[j]}) on {goniometer.depends[j]}. {goniometer.starts[j]} {goniometer.ends[j]} {goniometer.increments[j]}"
        )

    logger.info("")

    # Define rotation and translation axes
    OSC, TRANSL = ScanReader(
        goniometer.__dict__,
        data_type[0],
        n_images=data_type[1],
        snaked=params.input.snaked,
    )
    # Log scan information
    logger.info(f"Rotation scan axis: {list(OSC.keys())[0]}.")
    logger.info(
        f"Scan from {list(OSC.values())[0][0]} to {list(OSC.values())[0][-1]}.\n"
    )
    if TRANSL:
        logger.info(f"Scan along the {list(TRANSL.keys())} axes.")
        for k, v in TRANSL.items():
            logger.info(f"{k} scan from {v[0]} to {v[-1]}.")
    logger.info("\n")

    # Fix the number of images if not passed from command line.
    if data_type[0] == "images" and data_type[1] is None:
        data_type = ("images", len(list(OSC.values())[0]))
        logger.warning(f"Total number of images updated to: {data_type[1]}")
        logger.warning("\n")

    logger.info("Detector information:\n%s" % detector.description)
    logger.info(
        f"Sensor made of {detector.sensor_material} x {detector.sensor_thickness}"
    )
    if data_type[0] == "images":
        logger.info(f"Trusted pixels > {detector.underload} and < {detector.overload}")
    logger.info(
        f"Image is a {detector.image_size} array of {detector.pixel_size} pixels"
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

    logger.info("Start writing NeXus and data files ...")
    try:
        with h5py.File(master_file, "x") as nxsfile:
            write_NXentry(nxsfile)
            call_writers(
                nxsfile,
                datafiles,
                cf,
                data_type,
                goniometer.__dict__,
                detector.__dict__,
                module.__dict__,
                source.__dict__,
                beam.__dict__,
                attenuator.__dict__,
                OSC,
                TRANSL,
            )

            # Write VDS
            if data_type[0] == "images" and params.input.vds_writer == "dataset":
                logger.info(
                    "Calling VDS writer to write a Virtual Dataset under /entry/data/data"
                )
                image_vds_writer(nxsfile, (data_type[1], *detector.image_size))
            elif data_type[0] == "images" and params.input.vds_writer == "file":
                logger.info(
                    "Calling VDS writer to write a Virtual Dataset file and relative link."
                )
                vds_file_writer(
                    nxsfile, datafiles, (data_type[1], *detector.image_size)
                )
            else:
                logger.info("VDS won't be written.")
            # write_nexus_demo(
            #     nxsfile,
            #     data_file_template,
            #     data_type,
            #     cf,
            #     goniometer,
            #     detector,
            #     module,
            #     source,
            #     beam,
            #     attenuator,
            #     params.input.vds_writer,
            # )

            # Check and save pump status
            if params.pump_probe.pump_status is True:
                logger.info(
                    "Pump probe status is True, write relative metadata as NXnote."
                )
                pump_info = {
                    "pump_exposure_time": params.pump_probe.pump_exp,
                    "pump_delay": params.pump_probe.pump_delay,
                }
                write_NXnote(nxsfile, "/entry/source/notes", pump_info)

            # Record string with end_time
            end_time = datetime.fromtimestamp(time.time()).strftime(
                "%A, %d. %B %Y %I:%M%p"
            )

            # Write /entry/start_time and /entry/end_time
            timestamps = (get_iso_timestamp(start_time), get_iso_timestamp(end_time))
            logger.info("Writing timestamps to NeXus.")
            logger.info(f"Start time: {timestamps[0]}")
            logger.info(f"End time: {timestamps[1]}")
            write_NXdatetime(nxsfile, timestamps)
        logger.info(f"{master_file} correctly written.")
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.exception(err)

    logger.info("EOF")


def write_with_meta_cli(args):
    cl = meta_phil.command_line_argument_interpreter()
    working_phil = meta_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    # Path to meta file
    if params.input.metafile:
        metafile = Path(params.input.metafile).expanduser().resolve()
    else:
        sys.exit(
            "Please pass a _meta.h5 file. If not available use 'nexus' option instead."
        )

    # Get NeXus filename
    master_file = get_nexus_filename(metafile)

    # If no datafile has been passed, look for them in the directory
    if params.input.datafile:
        datafiles = [Path(d).expanduser().resolve() for d in params.input.datafile]
    else:
        datafile_pattern = (
            metafile.parent / f"{master_file.stem}_{6*'[0-9]'}.h5"
        ).as_posix()
        datafiles = [
            Path(d).expanduser().resolve() for d in sorted(glob.glob(datafile_pattern))
        ]

    # Start logger
    logfile = metafile.parent / "generate_nexus_from_meta.log"
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
    for tu in zip(goniometer.types, goniometer.units):
        assert tu in (
            ("translation", "mm"),
            ("rotation", "deg"),
        ), "Appropriate axis units should be: mm for translations, det for rotations"

    assert len(axis_vectors) == 3 * len(
        axes
    ), "Number of vectors does not match number of goniometer axes."

    for j in reversed(range(len(axes))):
        vector = axis_vectors[3 * j : 3 * j + 3]
        logger.info(
            f"Goniometer axis: {axes[j]} => {vector} ({goniometer.types[j]}) on {goniometer.depends[j]}. {goniometer.starts[j]} {goniometer.ends[j]} {goniometer.increments[j]}"
        )

    logger.info("")

    if detector.description is None:
        logger.warning("No detector description provided, exit.")
        sys.exit("Please provide a detector description for identification.")

    logger.info(
        f"Detector information:\n {detector.description}, {detector.detector_type}"
    )
    logger.info(
        f"Sensor made of {detector.sensor_material} x {detector.sensor_thickness}"
    )
    logger.info(f"Trusted pixels > {detector.underload} and < {detector.overload}")
    logger.info(
        f"Image is a {detector.image_size} array of {detector.pixel_size} pixels"
    )

    logger.info("Detector axes:")
    axes = detector.axes
    axis_vectors = detector.vectors
    for tu in zip(detector.types, detector.units):
        assert tu in (
            ("translation", "mm"),
            ("rotation", "deg"),
        ), "Appropriate axis units should be: mm for translations, det for rotations"

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

    if args.no_ow:
        logger.warning(f"The following datasets will not be overwritten: {args.no_ow}")
        metainfo = (metafile, args.no_ow)
    else:
        metainfo = (metafile, None)
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
                params.input.vds_writer,
                metainfo,
            )

            # Check and save pump status
            if params.pump_probe.pump_status is True:
                logger.info(
                    "Pump probe status is True, write relative metadata as NXnote."
                )
                pump_info = {
                    "pump_exposure_time": params.pump_probe.pump_exp,
                    "pump_delay": params.pump_probe.pump_delay,
                }
                write_NXnote(nxsfile, "/entry/source/notes", pump_info)

            logger.info(f"{master_file} correctly written.")
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.exception(err)

    logger.info("EOF")


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
    parents=[nexus_parser],
)
parser_NXmx.set_defaults(func=write_NXmx_cli)

parser_NXmx_demo = subparsers.add_parser(
    "2",
    aliases=["demo"],
    description=("Trigger NeXus and blank data file writing."),
    parents=[demo_parser, detectormode_parser],
)
parser_NXmx_demo.set_defaults(func=write_demo_cli)

parser_NXmx_meta = subparsers.add_parser(
    "3",
    aliases=["meta"],
    description=(
        "Trigger NeXus file writing pointing to an existing collection with a meta file."
    ),
    parents=[nexus_parser],
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
    # Define a stream handler
    CH = logging.StreamHandler(sys.stdout)
    CH.setLevel(logging.DEBUG)
    CH.setFormatter(formatter)
    logger.addHandler(CH)

    args = parser.parse_args()
    args.func(args)


# main()
