"""
Command line tool to generate NXmx-like NeXus files for Electron Diffraction.
"""
from __future__ import annotations

import argparse
import glob
import logging
import sys
from pathlib import Path

import freephil

from .. import log
from ..beamlines.ED_params import ED_coord_system
from ..nxs_utils import (
    Attenuator,
    Axis,
    Beam,
    Detector,
    Facility,
    Goniometer,
    SinglaDetector,
    Source,
    TransformationType,
)
from ..nxs_utils.ScanUtils import calculate_scan_points, identify_osc_axis
from ..nxs_write.NXmxWriter import EDNXmxFileWriter
from ..nxs_write.write_utils import find_number_of_images
from ..tools.ED_tools import extract_from_SINGLA_master, find_beam_centre
from ..utils import get_iso_timestamp, get_nexus_filename
from . import config_parser, nexus_parser, version_parser

logger = logging.getLogger("nexgen.EDNeXusGenerator")

ED_phil = freephil.parse(
    """
    input {
      datafiles = None
        .type = path
        .help = "List of input data files."
      vds_writer = None *dataset file
        .type = choice
        .help = "If not None, write vds along with external link to data in NeXus file, or create _vds.h5 file."
      n_imgs = None
        .type = int
        .help = "Total number of images collected."
      convert_to_mcstas = False
        .type = bool
        .help = "Convert vectors to mcstas if required. Defaults to False."
    }

    include scope nexgen.command_line.nxs_phil.goniometer_scope

    include scope nexgen.command_line.nxs_phil.instrument_scope

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
    # Define entry_key if dealing with singla detector
    data_entry_key = "/entry/data/data"

    # Get NeXus file name
    infile = datafiles[0].parent / datafiles[0].name.replace("_data", "")
    nxsfile = get_nexus_filename(infile)

    # Reset the location of the NeXus file if -o is parsed
    if args.output:
        newdir = Path(args.output).expanduser().resolve()
        nxsfile = newdir / nxsfile.name

    # Configure logger
    logfile = nxsfile.parent / "EDnxs.log"
    log.config(logfile.as_posix())

    logger.info("NeXus file writer for electron diffraction data from Singla.")
    logger.info(
        "Number of experiment data files in directory, linked to the Nexus file: %d"
        % len(datafiles)
    )
    logger.info("NeXus file will be saved as %s" % nxsfile)

    # Load technical info from phil parser
    # Get timestamps
    timestamps = (
        get_iso_timestamp(params.start_time),
        get_iso_timestamp(params.end_time),
    )

    # Define Source, Beam, Attenuator
    attenuator = Attenuator(transmission=None)
    beam = Beam(params.beam.wavelength)
    facility = Facility(
        params.source.name,
        params.source.short_name,
        params.source.type,
        params.source.facility_id,
    )
    source = Source(params.source.beamline_name, facility, params.source.probe)

    logger.info("Source information")
    logger.info(f"Facility: {source.name} - {source.facility_type}.")
    logger.info(f"Beamline / instrument: {source.beamline}")
    logger.info(f"Probe: {source.probe}")

    logger.warning("Have you checked the coordinate system convention?\n")

    # If anything has been passed regarding the new coordinate system convention
    # overwrite the existing dictionary
    if params.coord_system.convention:
        logger.info(
            f"New coordinate system convention: {params.coord_system.convention}."
        )
        ED_coord_system["convention"] = params.coord_system.convention
    else:
        logger.info("The following convention will be applied:\n" f"{ED_coord_system}")

    if params.coord_system.origin:
        logger.info(
            f"New value for coordinate system found: {params.coord_system.origin}."
        )
        ED_coord_system["origin"] = tuple(params.coord_system.origin)

    if params.coord_system.vectors:
        from .cli_utils import split_arrays

        # Note: setting to coordinate frame to avoid any conversions. FIXME
        vectors = split_arrays(["x", "y", "z"], params.coord_system.vectors)
        logger.info(
            f"New vectors defined for {params.coord_system.convention} coordinate system."
        )
        ED_coord_system["x"] = (".", "translation", "mm", vectors["x"])
        ED_coord_system["y"] = ("x", "translation", "mm", vectors["y"])
        ED_coord_system["z"] = ("y", "translation", "mm", vectors["z"])

    # Define Detector
    det_params = SinglaDetector(params.detector.description, params.detector.image_size)
    # Update detector params with info from master file
    if args.master:
        master = Path(args.master).expanduser().resolve()
        logger.info(
            "Looking through Dectris master file to extract at least mask and flatfield."
        )
        det_info = extract_from_SINGLA_master(master)
        det_params.constants.update(det_info)

        # Calculate beam centre if missing
        if params.detector.beam_center is None:
            beam_center = find_beam_centre(master, datafiles[0])
            logger.info(f"Calculated beam centre to be {beam_center}.")
            if beam_center is None:
                beam_center = (0, 0)
                logger.warning(
                    f"Unable to calculate beam centre. It has been set to {beam_center}."
                )
    else:
        beam_center = (
            params.detector.beam_center if params.detector.beam_center else (0, 0)
        )

    # Detector/ module axes
    det_axes = []
    for n, ax in enumerate(params.detector.axes):
        _tr = (
            TransformationType.TRANSLATION
            if params.detector.types[n] == "translation"
            else TransformationType.ROTATION
        )
        _vec = params.detector.vectors[3 * n : 3 * n + 3]
        _axis = Axis(
            ax,
            params.detector.depends[n],
            _tr,
            _vec,
            start_pos=params.detector.starts[n],
        )
        det_axes.append(_axis)
    fast_axis = tuple(params.detector_module.fast_axis)
    slow_axis = tuple(params.detector_module.slow_axis)
    detector = Detector(
        det_params,
        det_axes,
        beam_center,
        params.detector.exposure_time,
        [fast_axis, slow_axis],
    )
    logger.info(detector.__repr__())

    # Define Goniometer
    # Get gonio axes
    gonio_axes = []
    for n, ax in enumerate(params.goniometer.axes):
        _tr = (
            TransformationType.TRANSLATION
            if params.goniometer.types[n] == "translation"
            else TransformationType.ROTATION
        )
        _vec = params.goniometer.vectors[3 * n : 3 * n + 3]
        _axis = Axis(
            ax,
            params.goniometer.depends[n],
            _tr,
            _vec,
            start_pos=params.goniometer.starts[n],
            increment=params.goniometer.increments[n],
        )
        gonio_axes.append(_axis)
    # If n_images is not passed, calculate it from data files
    if not params.input.n_imgs:
        n_images = find_number_of_images(datafiles, data_entry_key)
        logger.info(f"Total number of images: {n_images}.")

    # Find scan
    scan_axis = identify_osc_axis(gonio_axes)
    scan_idx = [n for n, ax in enumerate(gonio_axes) if ax.name == scan_axis][0]
    gonio_axes[scan_idx].num_steps = n_images
    OSC = calculate_scan_points(
        gonio_axes[scan_idx],
        rotation=True,
        tot_num_imgs=n_images,
    )
    # No grid scan, can be added if needed at later time
    logger.info(f"Rotation scan axis: {list(OSC.keys())[0]}.")
    logger.info(
        f"Scan from {list(OSC.values())[0][0]} to {list(OSC.values())[0][-1]}.\n"
    )

    goniometer = Goniometer(gonio_axes, OSC)
    logger.info(goniometer.__repr__())

    # Start writing
    logger.info("Start writing NeXus file ...")
    try:
        EDFileWriter = EDNXmxFileWriter(
            nxsfile,
            goniometer,
            detector,
            source,
            beam,
            attenuator,
            n_images,
            ED_coord_system,
            convert_to_mcstas=params.input.convert_to_mcstas,
        )
        EDFileWriter.write(datafiles, data_entry_key)
        if params.input.vds_writer:
            logger.info(
                f"Calling VDS writer to write a Virtual Dataset{params.input.vds_writer}"
            )
            EDFileWriter.write_vds(
                writer_type=params.input.vds_writer,
                data_entry_key=data_entry_key,
                datafiles=datafiles,
            )
        else:
            logger.info("VDS won't be written.")
        EDFileWriter.update_timestamps(timestamps)

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
    description=("Trigger NeXus file writing for Singla data."),
    parents=[nexus_parser, config_parser],
)
singla_parser.add_argument(
    "-m",
    "--master",
    type=str,
    help="HDF5 master file written by Singla detector.",
)
singla_parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="Output directory if different from location of data files.",
)
singla_parser.set_defaults(func=write_from_SINGLA)


def main():
    args = parser.parse_args()
    args.func(args)
