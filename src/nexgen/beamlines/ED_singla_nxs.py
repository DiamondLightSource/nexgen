"""
Create a nexus file for electron diffraction collections using singla detector.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from .. import log
from ..nxs_utils import Attenuator, Beam, Detector, Goniometer, SinglaDetector
from ..nxs_utils.scan_utils import calculate_scan_points
from ..nxs_write.ed_nxmx_writer import EDNXmxFileWriter
from ..nxs_write.write_utils import find_number_of_images
from ..tools.ed_tools import (
    extract_detector_info_from_master,
    extract_exposure_time_from_master,
    extract_start_time_from_master,
    find_beam_centre,
)
from ..utils import coerce_to_path, find_in_dict, get_iso_timestamp, get_nexus_filename
from .ED_params import ED_coord_system, EDSingla, EDSource

logger = logging.getLogger("nexgen.EDNeXusWriter")

# Define entry_key if dealing with singla detector
SINGLA_DATA_ENTRY_KEY = "/entry/data/data"


def singla_nexus_writer(
    master_file: Path | str,
    det_distance: float,
    exp_time: float,
    ED_cs: Dict = ED_coord_system,
    datafiles: List[Path | str] = None,
    convert2mcstas: bool = False,
    **params,
):
    """Gather all collection parameters and write the NeXus file for an electron \
    diffraction collectio using SINGLA detector.

    Args:
        master_file (Path | str): Singla master file.
        det_distance (float): Sample-detector distance, in mm.
        exp_time (float): Exposure time, in s.
        ED_cs (Dict, optional): Definition of the ED coordinate system in use. Defaults to\
            {"convention": "ED",
            "origin": (0, 0, 0),
            "x": Axis("x", ".", "translation", [0, 1, 0]),
            "y":  Axis("y", "x", "translation", [-1, 0, 0]),
            "z":  Axis("z", "y", "translation", [0, 0, 1]),}
        datafiles (List[Path | str], optional): List of data files. Defaults to None.
        convert2mcstas (bool, optional): Convert vectors to mcstas if required. \
            Defaults to False.

    Keyword Args:
        n_imgs (int): Total number of images in collection.
        scan_axis (List[str, float, float]): Rotation axis name, start and increment.
        outdir (Path | str): Directory where to save the file. Only specify if different \
            from meta_file directory.
        beam_center (List[float, float]): Beam center position, in pixels.
        wavelength (float): Wavelength of incident beam, in A.
        start_time (datetime): Experiment start time.
        new_source_info (Dict): Information about Source that might differ from the default.\
            eg. {"facility_id": "MICROSCOPE", "name": "Not Diamond"}
        vds_writer (str): Write dataset or external file.
    """
    master_file = coerce_to_path(master_file)

    # Get NeXus filename
    nxsfile = get_nexus_filename(master_file)
    if find_in_dict("outdir", params) and params["outdir"]:
        wdir = coerce_to_path(params["outdir"])
        # Reset the location of the NeXus file
        nxsfile = wdir / nxsfile.name
    else:
        wdir = master_file.parent

    # Set up logging config
    logfile = wdir / "EDnxs.log"
    log.config(logfile.as_posix())

    logger.info("NeXus file writer for electron diffraction data from Singla.")
    logger.info(f"Collection directory: {master_file.parent}.")
    logger.info("NeXus file will be saved as %s" % nxsfile.name)

    # Data files
    if not datafiles:
        datafiles = [
            f
            for f in master_file.parent.iterdir()
            if nxsfile.stem + "_data" in f.as_posix()
        ]
    logger.info(f"{len(datafiles)} data files in directory.")

    # Total number of images
    if find_in_dict("n_imgs", params) and params["n_imgs"]:
        tot_num_imgs = params["n_imgs"]
    else:
        tot_num_imgs = find_number_of_images(datafiles, SINGLA_DATA_ENTRY_KEY)
    logger.info(f"Total number of images: {tot_num_imgs}.")

    # Get start_time timestamp in ISOformat
    if find_in_dict("start_time", params):
        start_time = get_iso_timestamp(params["start_time"])
    else:
        start_time = extract_start_time_from_master(master_file)

    # Update source if new info passed
    source = EDSource
    if find_in_dict("new_source_info", params):
        logger.warning("Updating source information.")
        for k, v in params["new_source_info"].items():
            source.__setattr__(k, v)
            logger.info(f"Source {k} now set to {v}.")
    logger.info(source.__repr__())

    # Define beam and attenuator
    attenuator = Attenuator(transmission=None)
    wl = params["wavelength"] if find_in_dict("wavelength", params) else None
    if not wl:
        logger.warning("Wavelength value was not set, it will default to 0.02 A.")
        wl = 0.02
    beam = Beam(wl)
    logger.info(f"Attenuation: {attenuator.transmission}")
    logger.info(f"Incident beam wavelength: {beam.wavelength}")

    # Define Singla detector
    det_params = SinglaDetector("Dectris Singla 1M", [1062, 1028])
    # Update detector params with info from master file
    logger.info(
        "Looking through Dectris master file to extract at least mask and flatfield."
    )
    det_info = extract_detector_info_from_master(master_file)
    det_params.constants.update(det_info)
    # If beam_centre not passed, define it
    if not find_in_dict("beam_center", params) or params["beam_center"] is None:
        beam_center = find_beam_centre(master_file, datafiles[0])
        logger.info(f"Calculated beam centre to be {beam_center}.")
        if beam_center is None:
            beam_center = (0, 0)
            logger.warning(
                f"Unable to calculate beam centre. It has been set to {beam_center}."
            )
    else:
        beam_center = params["beam_center"]

    # Detector/module axes
    det_axes = EDSingla.det_axes
    det_axes[0].start_pos = det_distance

    if not exp_time:
        logger.warning("Exposure time not set, trying to read it from the master file.")
        exp_time = extract_exposure_time_from_master(master_file)

    if not exp_time:
        raise ValueError(
            "Exposure time not provided. No 'count_time' in the master file."
        )

    # Define detector
    detector = Detector(
        det_params,
        det_axes,
        beam_center,
        exp_time,
        [EDSingla.fast_axis, EDSingla.slow_axis],
    )
    logger.info(detector.__repr__())

    # Goniometer
    gonio_axes = EDSingla.gonio
    if find_in_dict("scan_axis", params):
        gonio_axes[0].name = params["scan_axis"][0]
        gonio_axes[1].depends = params["scan_axis"][0]
        gonio_axes[0].start_pos = params["scan_axis"][1]
        gonio_axes[0].increment = params["scan_axis"][2]
        gonio_axes[0].num_steps = tot_num_imgs
    else:
        gonio_axes[0].num_steps = tot_num_imgs
    # No grid scan, can be added if needed at later time
    OSC = calculate_scan_points(
        gonio_axes[0],
        rotation=True,
        tot_num_imgs=tot_num_imgs,
    )
    logger.info(f"Rotation scan axis: {list(OSC.keys())[0]}.")
    logger.info(
        f"Scan from {list(OSC.values())[0][0]} to {list(OSC.values())[0][-1]}.\n"
    )

    goniometer = Goniometer(gonio_axes, OSC)
    logger.info(goniometer.__repr__())

    vds_writer = (
        "dataset" if not find_in_dict("vds_writer", params) else params["vds_writer"]
    )

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
            tot_num_imgs,
            ED_cs,
            convert_to_mcstas=convert2mcstas,
        )
        EDFileWriter.write(datafiles, SINGLA_DATA_ENTRY_KEY, start_time)
        if vds_writer:
            EDFileWriter.write_vds(
                writer_type=vds_writer,
                data_entry_key=SINGLA_DATA_ENTRY_KEY,
                datafiles=datafiles,
            )
        else:
            logger.info("VDS won't be written.")
        logger.info("NeXus file written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(f"An error occurred and {nxsfile} couldn't be written correctly.")
