"""
Tools to get the information stored inside the _meta.h5 file and overwrite the phil scope.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import h5py

from .. import units_of_length
from .Metafile import DectrisMetafile, TristanMetafile

# TODO actually define the type for scope extract and replace Any with Union
overwrite_logger = logging.getLogger("nexgen.MetaReader")
overwrite_logger.setLevel(logging.DEBUG)


def overwrite_beam(meta_file: h5py.File, name: str, beam: Dict | Any):
    """
    Looks for the wavelength value in the _meta.h5 file.
    If found, it overwrites the value that was parsed from the command line.

    Args:
        meta_file (h5py.File): Handle for _meta.h5 file.
        name (str): Detector description.
        beam (Dict | Any): Scope extract or dictionary defining the beam.

    Raises:
        ValueError: If an invalid detector description is passed. Allowed detectors for this function: Eiger.
    """
    if "eiger" in name.lower():
        meta = DectrisMetafile(meta_file)
        wl = meta.get_wavelength()
        if wl is None:
            overwrite_logger.info("No wavelength information found in meta file.")
            return
    else:
        raise ValueError("Unknown detector: please pass a valid detector description.")
    # If value exists, overwrite. Otherwise, create.
    overwrite_logger.warning("Wavelength will be overwritten.")
    overwrite_logger.info(f"Value for wavelength found in meta file: {wl}")
    if type(beam) is dict:
        beam["wavelength"] = wl
    else:
        try:
            beam.__dict__["wavelength"] = wl
        except KeyError:
            beam.__inject__("wavelength", wl)


def overwrite_detector(
    meta_file: h5py.File, detector: Dict | Any, ignore: List = None
) -> List:
    """
    Looks through the _meta.h5 file for informtion relating to NXdetector.

    Args:
        meta_file (h5py.File): Handle for _meta.h5 file.
        detector (Dict | Any): Scope extract or dictionary defining the detector.
        ignore (List, optional): List of datasets that should not be overwritten by the meta file. Defaults to None.

    Raises:
        ValueError: If an invalid detector description is passed. Allowed detectors for this function: Eiger, Tristan.

    Returns:
        link_list (List): A list of elements to be linked instead of copied in the NeXus file.
    """
    new_values = {}
    link_list = [[], []]
    if type(detector) is dict:
        detector_name = detector["description"].lower()
    else:
        detector_name = detector.description.lower()
    if "tristan" in detector_name:
        meta = TristanMetafile(meta_file)
        new_values["n_modules"] = meta.find_number_of_modules()
        new_values["meta_version"] = meta.find_meta_version()
        link_list[1].append("meta_version")
        overwrite_logger.info("Looking through meta file for Tristan detector.")
        overwrite_logger.info("Number of modules: %d" % new_values["n_modules"])
        overwrite_logger.info(
            "Found meta_version located at: %s " % new_values["meta_version"]
        )
    elif "eiger" in detector_name:
        meta = DectrisMetafile(meta_file)
        overwrite_logger.info("Looking through meta file for Eiger detector.")
        if meta.hasMask is True:
            overwrite_logger.info("Mask has been located in meta file")
            mask_info = meta.find_mask()
            new_values["pixel_mask"] = mask_info[0]
            new_values["pixel_mask_applied"] = mask_info[1]
            link_list[0].append("pixel_mask")
            link_list[0].append("pixel_mask_applied")
        if meta.hasFlatfield is True:
            overwrite_logger.info("Flatfield has been located in meta file")
            flatfield_info = meta.find_flatfield()
            new_values["flatfield"] = flatfield_info[0]
            new_values["flatfield_applied"] = flatfield_info[1]
            link_list[0].append("flatfield")
            link_list[0].append("flatfield_applied")
        if meta.hasDectrisGroup is True:
            new_values["software_version"] = meta.find_software_version()
            new_values["threshold_energy"] = meta.find_threshold_energy()
            new_values["bit_depth_readout"] = meta.find_bit_depth_readout()
            new_values["detector_readout_time"] = meta.find_detector_readout_time()
            new_values["serial_number"] = meta.find_detector_number()
            link_list[0].append("threshold_energy")
            link_list[0].append("bit_depth_readout")
            link_list[0].append("detector_readout_time")
            link_list[0].append("serial_number")
            link_list[1].append("software_version")
            pix = meta.get_pixel_size()
            new_values["pixel_size"] = [
                units_of_length(pix[0]),
                units_of_length(pix[1]),
            ]
            overwrite_logger.warning("Pixel_size will be overwritten.")
            overwrite_logger.info(
                f"Values for x and y pixel size found in meta file: {pix[0]}, {pix[1]}"
            )
            new_values["beam_center"] = meta.get_beam_center()
            overwrite_logger.warning("Beam_center will be overwritten.")
            overwrite_logger.info(
                f"Values for x and y beam center position found in meta file: "
                f"{new_values['beam_center']}"
            )
            sensor_info = meta.get_sensor_information()
            new_values["sensor_material"] = sensor_info[0]
            overwrite_logger.warning("Sensor material will be overwritten.")
            overwrite_logger.info(
                f"Value for sensor material found in meta file: {sensor_info[0]}"
            )
            new_values["sensor_thickness"] = units_of_length(sensor_info[1])
            overwrite_logger.warning("Sensor thickness will be overwritten.")
            overwrite_logger.info(
                f"Value for sensor thickness found in meta file: {sensor_info[1]}"
            )
            new_values["overload"] = meta.get_saturation_value()
            overwrite_logger.warning("Saturation value (overload) will be overwritten.")
            overwrite_logger.info(
                f"Value for overload found in meta file: {new_values['overload']}"
            )
    else:
        overwrite_logger.warning("Unknown detector, exit.")
        raise ValueError("Unknown detector: please pass a valid detector description.")

    if ignore:
        overwrite_logger.warning(
            f"The following datasets are not going to be overwritten: {ignore}"
        )
        for i in ignore:
            if i in new_values:
                del new_values[i]

    for k, v in new_values.items():
        if type(detector) is dict:
            detector[k] = v
        else:
            try:
                detector.__dict__[k] = v
            except KeyError:
                detector.__inject__(k, v)
    return link_list


def update_goniometer(meta_file: h5py.File, goniometer: Dict):
    """
    Read the axes values from the config/ dataset in the meta file and update the goniometer.

    Args:
        meta_file (h5py.File): Handle to Dectris-shaped meta.h5 file.
        goniometer (Dict): Dictionary containing all the goniometer axes information.
    """
    overwrite_logger.info(
        "Get goniometer axes values from meta file for Eiger detector."
    )
    meta = DectrisMetafile(meta_file)

    if meta.hasConfig is True:
        config = meta.read_config_dset()
        num = meta.get_number_of_images()

        goniometer["starts"] = []
        goniometer["ends"] = []
        goniometer["increments"] = []

        for ax in goniometer["axes"]:
            if f"{ax}_start" in config.keys():
                s = config[f"{ax}_start"]
                goniometer["starts"].append(s)
                overwrite_logger.info(f"Start value for axis {ax}: {s}.")
                inc = (
                    config[f"{ax}_increment"]
                    if f"{ax}_increment" in config.keys()
                    else 0.0
                )
                goniometer["increments"].append(inc)
                overwrite_logger.info(f"Increment value for axis {ax}: {inc}.")
                e = s + inc * num
                goniometer["ends"].append(e)
                overwrite_logger.info(f"End value for axis {ax}: {e}.")
            else:
                goniometer["starts"].append(0.0)
                goniometer["ends"].append(0.0)
                goniometer["increments"].append(0.0)
                overwrite_logger.info(f"Axis {ax} not in meta file, values set to 0.0.")
    else:
        overwrite_logger.warning(
            "No config/ dataset found in meta file. Goniometer axes value couldn't be updated from here."
        )
        return


def update_detector_axes(meta_file: h5py.File, detector: Dict):
    """
    Read the axes values from the config/ dataset in the meta file and update the detector.

    Args:
        meta_file (h5py.File): Handle to Dectris-shaped meta.h5 file.
        detector (Dict): Dictionary containing all the detector information.
    """
    overwrite_logger.info("Get detector axes values from meta file for Eiger detector.")
    meta = DectrisMetafile(meta_file)

    if meta.hasConfig is True:
        config = meta.read_config_dset()
        dist = units_of_length(meta.get_detector_distance())

        detector["starts"] = []
        detector["ends"] = []

        # First look for two_theta, then append det_z
        # For the moment, assume the detector doesn't move.
        for ax in detector["axes"]:
            if f"{ax}_start" in config.keys():
                s = config[f"{ax}_start"]
                detector["starts"].append(s)
                overwrite_logger.info(f"Position of axis {ax}: {s}.")

        detector["starts"].append(dist.to("mm").magnitude)
        overwrite_logger.info(f"Position of axis det_z: {dist.to('mm')}.")

        detector["ends"] = detector["starts"]
