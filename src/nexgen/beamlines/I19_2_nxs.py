"""
Create a NeXus file for time-resolved collections on I19-2.
"""

import glob
import logging
from collections import namedtuple
from pathlib import Path
from typing import List, Tuple

import h5py

from .. import get_iso_timestamp, get_nexus_filename, log
from ..nxs_write import calculate_scan_range, find_number_of_images, find_osc_axis
from ..nxs_write.NexusWriter import call_writers
from ..nxs_write.NXclassWriters import write_NXdatetime, write_NXentry
from ..tools.MetaReader import overwrite_beam, update_detector_axes, update_goniometer
from ..tools.VDS_tools import image_vds_writer
from .I19_2_params import (
    dset_links,
    eiger4M_params,
    goniometer_axes,
    source,
    tristan10M_params,
)

# Define a logger object
logger = logging.getLogger("nexgen.I19-2_NeXus")

# Tristan mask and flatfield files
maskfile = "Tristan10M_mask_with_spec.h5"
flatfieldfile = "Tristan10M_flat_field_coeff_with_Mo_17.479keV.h5"

# Define coordinate frame
coordinate_frame = "mcstas"

# Initialize dictionaries
goniometer = {}
detector = {}
module = {}
beam = {"flux": None}
attenuator = {}

tr_collect = namedtuple(
    "tr_collect",
    [
        "meta_file",
        "detector_name",
        "exposure_time",
        "transmission",
        "wavelength",
        "beam_center",
        "start_time",
        "stop_time",
        "scan_axis",
    ],
)

tr_collect.__doc__ = """Parameters passed as input from the beamline."""
tr_collect.meta_file.__doc__ = "Path to _meta.h5 file."
tr_collect.detector_name.__doc__ = "Name of the detector in use for current experiment."
tr_collect.exposure_time.__doc__ = "Exposure time, in s."
tr_collect.transmission.__doc__ = "Attenuator transmission, in %."
tr_collect.wavelength.__doc__ = "Incident beam wavelength, in A."
tr_collect.beam_center.__doc__ = "Beam center (x,y) position, in pixels."
tr_collect.start_time.__doc__ = "Collection start time."
tr_collect.stop_time.__doc__ = "Collection end time."
tr_collect.scan_axis.__doc__ = "Rotation scan axis. Must be passed for Tristan."


def tristan_writer(
    master_file: Path,
    TR: namedtuple,
    timestamps: Tuple[str, str] = (None, None),
    axes_pos: List[namedtuple] = None,
    det_pos: List[namedtuple] = None,
):
    """
    A function to call the nexus writer for Tristan 10M detector.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (namedtuple): Parameters passed from the beamline.
        timestamps (Tuple[str, str], optional): Collection start and end time. Defaults to (None, None).
        axes_pos (List[namedtuple], optional): List of (axis_name, start, end) values for the goniometer, passed from command line. Defaults to None.
        det_pos (List[namedtuple], optional): List of (axis_name, start) values for the detector, passed from command line. Defaults to None.
    """
    # Add tristan mask and flatfield files
    detector["pixel_mask"] = "Tristan10M_mask_with_spec.h5"
    detector["flatfield"] = "Tristan10M_flat_field_coeff_with_Mo_17.479keV.h5"

    # Update axes
    # Goniometer
    l = len(goniometer["axes"])
    goniometer["starts"] = l * [0.0]
    goniometer["increments"] = l * [0.0]
    goniometer["ends"] = l * [0.0]
    for ax in axes_pos:
        idx = goniometer["axes"].index(ax.id)
        goniometer["starts"][idx] = ax.start
        goniometer["ends"][idx] = ax.end

    # Detector
    detector["starts"] = detector["ends"] = len(detector["axes"]) * [0.0]
    for dax in det_pos:
        idx = detector["axes"].index(dax.id)
        detector["starts"][idx] = dax.start

    # Identify scan axis and calculate scan range
    if TR.scan_axis is None:
        scan_axis = find_osc_axis(
            goniometer["axes"],
            goniometer["starts"],
            goniometer["ends"],
            goniometer["types"],
        )
    else:
        scan_axis = TR.scan_axis
    scan_idx = goniometer["axes"].index(scan_axis)
    OSC = {scan_axis: (goniometer["starts"][scan_idx], goniometer["ends"][scan_idx])}

    logger.info("--- COLLECTION SUMMARY ---")
    logger.info("Source information")
    logger.info(f"Facility: {source['name']} - {source['type']}.")
    logger.info(f"Beamline: {source['beamline_name']}")

    logger.info(f"Incident beam wavelength: {beam['wavelength']}")
    logger.info(f"Attenuation: {attenuator['transmission']}")

    logger.info("Goniometer information")
    logger.info(f"Scan axis is: {scan_axis}")
    for j in range(len(goniometer["axes"])):
        logger.info(
            f"Goniometer axis: {goniometer['axes'][j]} => {goniometer['starts'][j]}, {goniometer['types'][j]} on {goniometer['depends'][j]}"
        )
    logger.info("Detector information")
    logger.info(f"{detector['description']}")
    logger.info(
        f"Sensor made of {detector['sensor_material']} x {detector['sensor_thickness']}"
    )
    logger.info(
        f"Detector is a {detector['image_size'][::-1]} array of {detector['pixel_size']} pixels"
    )
    for k in range(len(detector["axes"])):
        logger.info(
            f"Detector axis: {detector['axes'][k]} => {detector['starts'][k]}, {detector['types'][k]} on {detector['depends'][k]}"
        )

    logger.info(f"Recorded beam center is: {detector['beam_center']}.")

    logger.info(f"Timestamps recorded: {timestamps}")

    # Write
    try:
        with h5py.File(master_file, "x") as nxsfile:
            write_NXentry(nxsfile)

            if timestamps[0]:
                write_NXdatetime(nxsfile, (timestamps[0], None))

            call_writers(
                nxsfile,
                [TR.meta_file],
                coordinate_frame,
                (detector["mode"], None),
                goniometer,
                detector,
                module,
                source,
                beam,
                attenuator,
                OSC,
            )

            if timestamps[1]:
                write_NXdatetime(nxsfile, (None, timestamps[1]))
            logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )


def eiger_writer(
    master_file: Path,
    TR: namedtuple,
    timestamps: Tuple[str, str] = (None, None),
):
    """
    A function to call the nexus writer for Eiger 2X 4M detector.
    It requires the informatin contained inside the meta file to work correctly.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (namedtuple): Parameters passed from the beamline.
        timestamps (Tuple[str, str], optional): Collection start and end time. Defaults to (None, None).

    Raises:
        IOError: If the axes positions can't be read from the metafile (missing config or broken links).
    """
    # Find datafiles
    logger.info("Looking for data files ...")
    filename_template = (
        TR.meta_file.parent / TR.meta_file.name.replace("meta", f"{6*'[0-9]'}")
    ).as_posix()
    filenames = [
        Path(f).expanduser().resolve() for f in sorted(glob.glob(filename_template))
    ]
    # Calculate total number of images
    n_frames = find_number_of_images(filenames)
    logger.info(
        f"Found {len(filenames)} files in directory, containing {n_frames} images."
    )

    # Update axes
    with h5py.File(TR.meta_file, "r") as mh:
        update_goniometer(mh, goniometer)
        update_detector_axes(mh, detector)
        logger.info(
            "Goniometer and detector axes positions have been updated with values from the meta file."
        )
        if beam["wavelength"] is None:
            logger.info(
                "Wavelength has't been passed by user. Looking for it in the meta file."
            )
            overwrite_beam(mh, TR.detector_name, beam)
        if detector["beam_center"] is None:
            logger.info(
                "Beam center position has't been passed by user. Looking for it in the meta file."
            )
            from ..tools.Metafile import DectrisMetafile

            meta = DectrisMetafile(mh)
            detector["beam_center"] = meta.get_beam_center()

    # Check that axes have been updated
    if goniometer["starts"] is None:
        raise IOError("Goniometer axes values couldn't be read from meta file.")
        # FOr now. If it doesn't work, more than likely meta is broken but axes can be passed.
    if detector["starts"] is None:
        raise IOError("Detector axes values couldn't be read from meta file.")

    # Identify scan axis and calculate scan range
    scan_axis = find_osc_axis(
        goniometer["axes"],
        goniometer["starts"],
        goniometer["ends"],
        goniometer["types"],
    )
    scan_idx = goniometer["axes"].index(scan_axis)
    OSC = calculate_scan_range(
        [scan_axis],
        [goniometer["starts"][scan_idx]],
        [goniometer["ends"][scan_idx]],
        axes_increments=[goniometer["increments"][scan_idx]],
        # n_images=n_frames,
        rotation=True,
    )

    logger.info("--- COLLECTION SUMMARY ---")
    logger.info("Source information")
    logger.info(f"Facility: {source['name']} - {source['type']}.")
    logger.info(f"Beamline: {source['beamline_name']}")

    logger.info(f"Incident beam wavelength: {beam['wavelength']}")
    logger.info(f"Attenuation: {attenuator['transmission']}")

    logger.info("Goniometer information")
    logger.info(f"Scan axis is: {scan_axis}")
    for j in range(len(goniometer["axes"])):
        logger.info(
            f"Goniometer axis: {goniometer['axes'][j]} => {goniometer['starts'][j]}, {goniometer['types'][j]} on {goniometer['depends'][j]}"
        )
    logger.info("Detector information")
    logger.info(f"{detector['description']}")
    logger.info(
        f"Sensor made of {detector['sensor_material']} x {detector['sensor_thickness']}"
    )
    logger.info(
        f"Detector is a {detector['image_size'][::-1]} array of {detector['pixel_size']} pixels"
    )
    for k in range(len(detector["axes"])):
        logger.info(
            f"Detector axis: {detector['axes'][k]} => {detector['starts'][k]}, {detector['types'][k]} on {detector['depends'][k]}"
        )

    logger.info(f"Recorded beam center is: {detector['beam_center']}.")

    logger.info(f"Timestamps recorded: {timestamps}")

    # Write
    try:
        with h5py.File(master_file, "x") as nxsfile:
            write_NXentry(nxsfile)

            if timestamps[0]:
                write_NXdatetime(nxsfile, (timestamps[0], None))

            call_writers(
                nxsfile,
                filenames,
                coordinate_frame,
                (detector["mode"], n_frames),
                goniometer,
                detector,
                module,
                source,
                beam,
                attenuator,
                OSC,
                transl_scan=None,
                metafile=TR.meta_file,
                link_list=dset_links,
            )

            if timestamps[1]:
                write_NXdatetime(nxsfile, (None, timestamps[1]))

            # Write VDS
            image_vds_writer(nxsfile, (int(n_frames), *detector["image_size"]))
            logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )


def nexus_writer(**params):
    """
    Gather all parameters from the beamline and call the NeXus writers.
    """
    TR = tr_collect(
        meta_file=Path(params["meta_file"]).expanduser().resolve(),
        detector_name=params["detector_name"],
        exposure_time=params["exposure_time"],
        transmission=params["transmission"],
        wavelength=params["wavelength"],
        beam_center=params["beam_center"],
        start_time=params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")  #
        if params["start_time"]
        else None,
        stop_time=params["stop_time"].strftime("%Y-%m-%dT%H:%M:%S")  #
        if params["stop_time"]
        else None,
        scan_axis=params["scan_axis"] if params["scan_axis"] else None,
    )

    # Check that the new NeXus file is to be written in the same directory
    if params["outdir"]:
        wdir = Path(params["outdir"]).expanduser().resolve()
    else:
        wdir = TR.meta_file.parent

    # Define a file handler
    logfile = wdir / "I19_2_nxs_writer.log"
    # Configure logging
    log.config(logfile.as_posix())

    logger.info("NeXus file writer for beamline I19-2 at DLS.")
    logger.info(f"Detector in use for this experiment: {TR.detector_name}.")
    logger.info(f"Current collection directory: {TR.meta_file.parent}")
    # Add some information to logger
    logger.info("Creating a NeXus file for %s ..." % TR.meta_file.name)
    # Get NeXus filename
    master_file = get_nexus_filename(TR.meta_file)
    master_file = wdir / master_file.name
    logger.info("NeXus file will be saved as %s" % master_file)

    # Get timestamps in the correct format if they aren't already
    timestamps = (
        get_iso_timestamp(TR.start_time),
        get_iso_timestamp(TR.stop_time),
    )

    # logger.info("Load goniometer from I19-2.")
    for k, v in goniometer_axes.items():
        goniometer[k] = v

    # Fill in a few dictionaries
    attenuator["transmission"] = TR.transmission if TR.transmission else None

    beam["wavelength"] = TR.wavelength

    if "tristan" in TR.detector_name.lower():
        for k, v in tristan10M_params.items():
            detector[k] = v
        if params["gonio_pos"] is None or params["det_pos"] is None:
            logger.error("Please pass the axes positions for a Tristan collection.")
        if TR.scan_axis is None:
            logger.warning("No scan axis has been specified.")
    else:
        for k, v in eiger4M_params.items():
            detector[k] = v

    detector["exposure_time"] = TR.exposure_time
    detector["beam_center"] = TR.beam_center

    # Module
    module["fast_axis"] = detector.pop("fast_axis")
    module["slow_axis"] = detector.pop("slow_axis")
    # Set value for module_offset calculation.
    module["module_offset"] = "1"

    if "eiger" in TR.detector_name.lower():
        eiger_writer(master_file, TR, timestamps)
    elif "tristan" in TR.detector_name.lower():
        tristan_writer(
            master_file, TR, timestamps, params["gonio_pos"], params["det_pos"]
        )
