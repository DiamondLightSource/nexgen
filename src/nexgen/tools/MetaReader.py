"""
Tools to get the information stored inside the _meta.h5 file and overwrite the phil scope.
"""
# TODO add more logging

import h5py
import logging

from typing import List

from nexgen.tools.Metafile import DectrisMetafile, TristanMetafile

from .. import units_of_length

# from Metafile import DectrisMetafile, TristanMetafile

overwrite_logger = logging.getLogger("NeXusGenerator.writer.overwrite")


def overwrite_beam(meta_file: h5py.File, name: str, beam):
    """
    TODO Add docstring here
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


def overwrite_detector(meta_file: h5py.File, detector) -> List:
    """
    TODO Add docstring here
    """
    new_values = {}
    link_list = [[], []]
    if "tristan" in detector.description.lower():
        meta = TristanMetafile(meta_file)
        new_values["n_modules"] = meta.find_number_of_modules()
        new_values["meta_version"] = meta.find_meta_version()
        link_list[1].append("meta_version")
    elif "eiger" in detector.description.lower():
        meta = DectrisMetafile(meta_file)
        if meta.hasMask is True:
            mask_info = meta.find_mask()
            new_values["pixel_mask"] = mask_info[0]
            new_values["pixel_mask_applied"] = mask_info[1]
            link_list.append("pixel_mask")
            link_list[0].append("pixel_mask_applied")
        if meta.hasFlatfield is True:
            flatfield_info = meta.find_flatfield()
            new_values["flatfield"] = flatfield_info[0]
            new_values["flatfield_applied"] = flatfield_info[1]
            link_list[0].append("flatfield")
            link_list[0].append("flatfield_applied")
        if meta.hasDectrisGroup is True:
            new_values["software_version"] = meta.find_software_version()
            new_values["threshold_energy"] = meta.find_threshold_energy()
            new_values["bit_depth_readout"] = meta.find_bit_depth_readout()
            new_values["detector_readout_time"] = meta.find_
            pix = meta.get_pixel_size()
            new_values["pixel_size"] = [
                units_of_length(pix[0]),
                units_of_length(pix[1]),
            ]
            new_values["beam_center"] = meta.get_beam_center()
            sensor_info = meta.get_sensor_information()
            new_values["sensor_material"] = sensor_info[0]
            new_values["sensor_thickness"] = units_of_length(sensor_info[1])
            link_list[0].append("threshold_energy")
            link_list[0].append("bit_depth_readout")
            link_list[1].append("software_version")
    else:
        overwrite_logger.warning("Unknown detector, exit.")
        raise ValueError("Please pass a valid detector description.")

    for k, v in new_values.items():
        try:
            detector.__dict__[k] = v
        except KeyError:
            detector.__inject__(k, v)
    return link_list
