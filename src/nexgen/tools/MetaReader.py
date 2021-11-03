"""
Tools to get the information stored inside the _meta.h5 file and overwrite the phil scope.
"""

import h5py
import logging

from typing import List

from .. import units_of_length

from .Metafile import DectrisMetafile, TristanMetafile

overwrite_logger = logging.getLogger("NeXusGenerator.writer.from_meta")


def overwrite_beam(meta_file: h5py.File, name: str, beam):
    """
    Looks for the wavelength value in the _meta.h5 file.
    If found, it overwrites the value that was parsed from the command line.

    Args:
        meta_file:  _meta.h5 file.
        name:       Detector description.
        beam:       Scope extract defining the beam.
    """
    if "eiger" in name.lower():
        meta = DectrisMetafile(meta_file)
        wl = meta.get_wavelength()
        if wl is None:
            overwrite_logger.info("No wavelength information found in meta file.")
            return
    else:
        raise ValueError("Please pass a valid detector description.")
    # If value exists, overwrite. Otherwise, create.
    overwrite_logger.warning("Wavelength will be overwritten.")
    overwrite_logger.info(f"Value for wavelngth found in meta file: {wl}")
    try:
        beam.__dict__["wavelength"] = wl
    except KeyError:
        beam.__inject__("wavelength", wl)


def overwrite_detector(meta_file: h5py.File, detector, ignore: List = None) -> List:
    """
    Looks through the _meta.h5 file for informtion relating to NXdetector.

    Args:
        meta_file:  _meta.h5 file.
        detector:   Scope extract defining the detector.
        ignore:     List of datasets that should not be overwritten by the meta file.
    Returns:
        link_list:  A list of elements to be linked instead of copied in the NeXus file.
    """
    new_values = {}
    link_list = [[], []]
    if "tristan" in detector.description.lower():
        meta = TristanMetafile(meta_file)
        new_values["n_modules"] = meta.find_number_of_modules()
        new_values["meta_version"] = meta.find_meta_version()
        link_list[1].append("meta_version")
        overwrite_logger.info("Looking through meta file for Tristan detector.")
        overwrite_logger.info("Number of modules: %d" % new_values["n_modules"])
        overwrite_logger.info(
            "Found meta_version located at: %s " % new_values["meta_version"]
        )
    elif "eiger" in detector.description.lower():
        meta = DectrisMetafile(meta_file)
        overwrite_logger.info("Looking through meta file for Eiger detector.")
        if meta.hasMask is True:
            overwrite_logger.info("Mask has been located in meta file")
            mask_info = meta.find_mask()
            new_values["pixel_mask"] = mask_info[0]
            new_values["pixel_mask_applied"] = mask_info[1]
            link_list.append("pixel_mask")
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
                f"Values for x and y beam center position found in meta file: %s"
                % new_values["beam_center"]
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
    else:
        overwrite_logger.warning("Unknown detector, exit.")
        raise ValueError("Please pass a valid detector description.")

    if ignore:
        overwrite_logger.warning(
            f"The following datasets are not going to be overwritten: {ignore}"
        )
        for i in ignore:
            if i in new_values:
                del new_values[i]

    for k, v in new_values.items():
        try:
            detector.__dict__[k] = v
        except KeyError:
            detector.__inject__(k, v)
    return link_list


# TODO add provision in case something actually is None
