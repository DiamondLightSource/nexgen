"""
Command line tool to generate NeXus files.
"""

import argparse
import glob
import logging
import time
from pathlib import Path

import numpy as np

from nexgen import log
from nexgen.command_line.cli_config import CliConfig
from nexgen.command_line.parse_utils import (
    CheckFileExtensionAction,
    ImportCollectAction,
    config_parser,
    vds_parser,
    version_parser,
)
from nexgen.nxs_utils import Detector, Goniometer
from nexgen.nxs_utils.scan_utils import (
    calculate_scan_points,
    identify_grid_scan_axes,
    identify_osc_axis,
)
from nexgen.nxs_write.nxmx_writer import EventNXmxFileWriter, NXmxFileWriter
from nexgen.nxs_write.write_utils import find_number_of_images
from nexgen.tools.data_writer import generate_event_files, generate_image_files
from nexgen.utils import (
    get_filename_template,
    get_iso_timestamp,
    get_nexus_filename,
    units_of_time,
)

USAGE = "%(prog)s <sub-command> filename [options]"

# Define a logger object
logger = logging.getLogger("nexgen.NeXusGenerator")


def _get_datafiles(filepath: Path, filename_root: str) -> list[Path]:
    _file_template = filepath / f"{filename_root}_*.h5"
    datafiles = [
        Path(f).expanduser().resolve()
        for f in glob.glob(_file_template.as_posix())
        if "meta.h5" not in f
    ]
    return datafiles


def write_nxmx_cli(args):
    params = CliConfig.from_file(args.config)

    filepath = Path(args.visitpath)
    wdir = args.outdir if args.outdir else args.visitpath
    # Start logger
    logfile = wdir / "generate_nexus.log"
    # Configure logging
    log.config(logfile.as_posix())

    # Path to data files
    datafiles = _get_datafiles(filepath, args.filename_root)

    # Get meta file
    # meta_file = Path(args.input_file) if "meta.h5" in args.input_file else filepath / f"{args.filename_root}_meta.h5"

    # Get nexus filename
    master_file = wdir / get_nexus_filename(datafiles[0]).name

    logger.info("NeXus file writer for existing dataset.")

    # Add some information to logger
    logger.info("Create a NeXus file for %s" % datafiles[0])
    logger.info(
        "Number of experiment data files in directory, linked to the Nexus file: %d"
        % len(datafiles)
    )
    logger.info("NeXus file will be saved as %s" % master_file)

    # Define images vs events based on detector mode
    logger.info(f"Data type: {params.det.mode}.")
    if params.det.mode == "images":
        num_images = find_number_of_images(datafiles)
        logger.info(f"Total number of images: {num_images}")
        if params.gonio.scan_type == "rotation":
            scan_axis = identify_osc_axis(params.gonio.axes)
            scan_idx = [
                n for n, ax in enumerate(params.gonio.axes) if ax.name == scan_axis
            ][0]
            params.gonio.axes[scan_idx].num_steps = num_images
            scan = calculate_scan_points(
                params.gonio.axes[scan_idx],
                rotation=True,
                tot_num_imgs=num_images,
            )
        else:
            grid_axes = identify_grid_scan_axes(params.gonio.axes)
            scan = calculate_scan_points(
                *grid_axes, snaked=params.gonio.snaked_scan, tot_num_imgs=num_images
            )
    else:
        # Usually a rotation
        # Calculate scan range
        scan_idx = [
            n
            for n, ax in enumerate(params.gonio.axes)
            if ax.name == params.gonio.scan_axis
        ][0]
        scan_pos = (
            params.gonio.axes[scan_idx].start_pos,
            params.gonio.axes[scan_idx].end_pos,
        )
        scan = {params.gonio.scan_axis: scan_pos}

    goniometer = Goniometer(params.gonio.axes, scan=scan)
    detector = Detector(
        params.det.params,
        params.det.axes,
        params.det.beam_center,
        params.det.exposure_time,
        [params.det.module.fast_axis, params.det.module.slow_axis],
    )

    # Log information
    logger.info("Source information")
    logger.info(
        f"Facility: {params.instrument.source.facility.name} - {params.instrument.source.facility.type}."
    )
    logger.info(f"Beamline / Instrument: {params.instrument.source.beamline}")

    logger.debug(f"Incident beam wavelength: {params.instrument.beam.wavelength}")
    logger.debug(f"Attenuation: {params.instrument.attenuator.transmission}")

    logger.debug(goniometer.__repr__())
    logger.debug(detector.__repr__())

    logger.debug(f"Recorded beam center is: {detector.beam_center}.")
    logger.debug(f"Recorded exposure time: {detector.exp_time} s.")

    try:
        # Aaaaaaaaaaaand write
        if params.det.mode == "images":
            writer = NXmxFileWriter(
                master_file,
                goniometer,
                detector,
                params.instrument.source,
                params.instrument.beam,
                params.instrument.attenuator,
                num_images,
            )
            writer.write(image_datafiles=datafiles)
            if not args.no_vds:
                writer.write_vds(args.vds_offset)
        else:
            writer = EventNXmxFileWriter(
                master_file,
                goniometer,
                detector,
                params.instrument.source,
                params.instrument.beam,
                params.instrument.attenuator,
            )
            writer.write()
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.exception(err)

    logger.info("EOF\n")


def write_demo_cli(args):
    params = CliConfig.from_file(args.config)

    master_file = Path(args.master_file)
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
    logger.info("NeXus file will be saved as %s" % master_file)
    logger.info("Data file(s) template: %s" % data_file_template)

    # Images or events ?
    # Figure out how many files will need to be written
    logger.info("Calculating number of files to write ...")
    if params.det.mode == "events":
        num_events = args.num if args.num else 1
        # Determine the number of files. Write one file per module.
        # Either a 10M or a 1M, no other possibilities at this moment.
        n_files = 10 if "10M" in params.det.params.description.upper() else 1
    else:
        num_images = args.num if args.num else 1000
        # The maximum number of images being written each dataset is 1000
        if num_images <= 1000:
            n_files = 1
        else:
            n_files = int(np.ceil(num_images / 1000))

    logger.info("%d file(s) containing blank data to be written." % n_files)

    # Get datafile list
    datafiles = [
        Path(data_file_template % (n + 1)).expanduser().resolve()
        for n in range(n_files)
    ]

    logger.info("Calling data writer ...")
    # Write data files
    if params.det.mode == "images":
        generate_image_files(
            datafiles,
            params.det.params.image_size,
            params.det.params.description,
            num_images,
        )
    else:
        exp_time = units_of_time(params.det.exposure_time)
        generate_event_files(
            datafiles, num_events, params.det.params.description, exp_time.magnitude
        )

    logger.info("\n")

    # Record string with start_time
    start_time = get_iso_timestamp(time.time())

    # Define images vs events based on detector mode
    logger.info(f"Data type: {params.det.mode}.")
    if params.det.mode == "images":
        num_images = find_number_of_images(datafiles)
        logger.info(f"Total number of images: {num_images}")
        if params.gonio.scan_type == "rotation":
            scan_axis = identify_osc_axis(params.gonio.axes)
            scan_idx = [
                n for n, ax in enumerate(params.gonio.axes) if ax.name == scan_axis
            ][0]
            params.gonio.axes[scan_idx].num_steps = num_images
            scan = calculate_scan_points(
                params.gonio.axes[scan_idx],
                rotation=True,
                tot_num_imgs=num_images,
            )
        else:
            grid_axes = identify_grid_scan_axes(params.gonio.axes)
            scan = calculate_scan_points(
                *grid_axes, snaked=params.gonio.snaked_scan, tot_num_imgs=num_images
            )
    else:
        # Usually a rotation
        # Calculate scan range
        scan_idx = [
            n
            for n, ax in enumerate(params.gonio.axes)
            if ax.name == params.gonio.scan_axis
        ][0]
        scan_pos = (
            params.gonio.axes[scan_idx].start_pos,
            params.gonio.axes[scan_idx].end_pos,
        )
        scan = {params.gonio.scan_axis: scan_pos}

    goniometer = Goniometer(params.gonio.axes, scan=scan)
    detector = Detector(
        params.det.params,
        params.det.axes,
        params.det.beam_center,
        params.det.exposure_time,
        [params.det.module.fast_axis, params.det.module.slow_axis],
    )

    # Update location of map and flatfield if passed
    if args.flatfield:
        logger.info(
            f"Flatfield correction data lives here {args.flatfield}, updating detector info."
        )
        detector.detector_params.constants["flatfield"] = args.flatfield

    if args.mask:
        logger.info(f"Bad pixel mask lives here {args.mask}, updating detector info")
        detector.detector_params.constants["pixel_mask"] = args.pixel_mask

    # Log information
    logger.info("Source information")
    logger.info(
        f"Facility: {params.instrument.source.facility.name} - {params.instrument.source.facility.type}."
    )
    logger.info(f"Beamline / Instrument: {params.instrument.source.beamline}")

    logger.debug(f"Incident beam wavelength: {params.instrument.beam.wavelength}")
    logger.debug(f"Attenuation: {params.instrument.attenuator.transmission}")

    logger.debug(goniometer.__repr__())
    logger.debug(detector.__repr__())

    logger.debug(f"Recorded beam center is: {detector.beam_center}.")
    logger.debug(f"Recorded exposure time: {detector.exp_time} s.")

    try:
        # Aaaaaaaaaaaand write
        if params.det.mode == "images":
            writer = NXmxFileWriter(
                master_file,
                goniometer,
                detector,
                params.instrument.source,
                params.instrument.beam,
                params.instrument.attenuator,
                num_images,
            )
            writer.write(image_datafiles=datafiles, start_time=start_time)
            if not args.no_vds:
                writer.write_vds(args.vds_offset)
        else:
            writer = EventNXmxFileWriter(
                master_file,
                goniometer,
                detector,
                params.instrument.source,
                params.instrument.beam,
                params.instrument.attenuator,
            )
            writer.write(start_time=start_time)
    except Exception as err:
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        logger.exception(err)

    logger.info("EOF\n")


def _parse_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        usage=USAGE,
        parents=[version_parser],
    )
    subparsers = parser.add_subparsers(
        help="Choose whether to write a NXmx NeXus file for a collection or a demo with fake data. \
            Run generate_nexus <command> --help to see the parameters for each sub-command.",
        required=True,
        dest="sub-command",
    )

    nxmx_parser = subparsers.add_parser(
        "1",
        aliases=["nxmx"],
        description=("Trigger NXmx NeXus file writing pointing to existing data."),
        parents=[config_parser, vds_parser],
    )
    nxmx_parser.add_argument(
        "input_file",
        type=str,
        action=ImportCollectAction,
        help="Path to _meta.h5 file or data_00001.h5 file for the collection.",
    )
    nxmx_parser.add_argument(
        "-o",
        "--outdir",
        type=str,
        help="Output directory for nexus file, if different from collection location.",
    )
    nxmx_parser.add_argument(
        "-nxs",
        "--nxs-filename",
        type=str,
        help="New nexus filename if stem needs to be different from data files.",
    )
    nxmx_parser.set_defaults(func=write_nxmx_cli)
    demo_parser = subparsers.add_parser(
        "2",
        aliases=["demo"],
        description=(
            "Trigger NeXus and blank data file writing. "
            "This option always requires either the -i or -e flags, which are \
                mutually exclusive arguments."
        ),
        parents=[config_parser, vds_parser],
    )
    demo_parser.add_argument(
        "master_file",
        type=str,
        action=CheckFileExtensionAction,
        help="Filename for the master file to be written. All data files will \
            have the format filename.stem_#####.h5.",
    )
    demo_parser.add_argument(
        "-n",
        "--num",
        type=int,
        help="Number of blank images/events to write to file. If not passed, \
            will default to 1 chunk for events or 1000 images.",
    )
    demo_parser.add_argument(
        "--flatfield",
        type=str,
        help="Path to flatfield file if it exists.",
    )
    demo_parser.add_argument(
        "--mask", type=str, help="Path to pixel mask file if it exists."
    )
    demo_parser.set_defaults(func=write_demo_cli)
    return parser


def main():
    parser = _parse_cli()
    args = parser.parse_args()
    args.func(args)
