"""
Tools to get the information stored inside the _meta.h5 file and overwrite the phil scope.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import h5py
import numpy as np
from numpy.typing import DTypeLike

from ..nxs_utils import Axis
from ..utils import ScopeExtract, units_of_length
from .metafile import DectrisMetafile, TristanMetafile

# TODO actually define the type for scope extract and replace Any with Union
overwrite_logger = logging.getLogger("nexgen.MetaReader")
overwrite_logger.setLevel(logging.DEBUG)


def overwrite_beam(meta_file: h5py.File, name: str, beam: Dict | ScopeExtract):
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
            overwrite_logger.warning("No wavelength information found in meta file.")
            return
    else:
        raise ValueError("Unknown detector: please pass a valid detector description.")
    # If value exists, overwrite. Otherwise, create.
    overwrite_logger.warning("Wavelength will be overwritten.")
    overwrite_logger.info(f"Value for wavelength found in meta file: {wl}")
    if isinstance(beam, dict):
        beam["wavelength"] = wl
    else:
        try:
            beam.__dict__["wavelength"] = wl
        except KeyError:
            beam.__inject__("wavelength", wl)


def overwrite_detector(
    meta_file: h5py.File, detector: Dict | ScopeExtract, ignore: List = None
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
    if isinstance(detector, dict):
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
            overwrite_logger.debug("Mask has been located in meta file")
            mask_info = meta.find_mask()
            new_values["pixel_mask"] = mask_info[0]
            new_values["pixel_mask_applied"] = mask_info[1]
            link_list[0].append("pixel_mask")
            link_list[0].append("pixel_mask_applied")
        if meta.hasFlatfield is True:
            overwrite_logger.debug("Flatfield has been located in meta file")
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
            overwrite_logger.debug(
                f"Values for x and y pixel size found in meta file: {pix[0]}, {pix[1]}"
            )
            new_values["beam_center"] = meta.get_beam_center()
            overwrite_logger.warning("Beam_center will be overwritten.")
            overwrite_logger.debug(
                f"Values for x and y beam center position found in meta file: "
                f"{new_values['beam_center']}"
            )
            sensor_info = meta.get_sensor_information()
            new_values["sensor_material"] = sensor_info[0]
            overwrite_logger.warning("Sensor material will be overwritten.")
            overwrite_logger.debug(
                f"Value for sensor material found in meta file: {sensor_info[0]}"
            )
            new_values["sensor_thickness"] = units_of_length(sensor_info[1])
            overwrite_logger.warning("Sensor thickness will be overwritten.")
            overwrite_logger.debug(
                f"Value for sensor thickness found in meta file: {sensor_info[1]}"
            )
            new_values["overload"] = meta.get_saturation_value()
            overwrite_logger.warning("Saturation value (overload) will be overwritten.")
            overwrite_logger.debug(
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
        if isinstance(detector, dict):
            detector[k] = v
        else:
            try:
                detector.__dict__[k] = v
            except KeyError:
                detector.__inject__(k, v)
    return link_list


def define_vds_data_type(meta_file: DectrisMetafile) -> DTypeLike:
    """Define the data type for the VDS from the bit_depth defined in the meta file.

    Args:
        meta_file (DectrisMetafile): Handle to Dectris-shaped meta.h5 file.

    Returns:
        DTypeLike: Data type as np.uint##.
    """
    overwrite_logger.debug("Define dtype for VDS creating from bit_depth_image.")
    # meta = DectrisMetafile(meta_file)

    nbits = meta_file.get_bit_depth_image()
    overwrite_logger.debug(f"Found value for bit_depth_image: {nbits}.")
    if nbits == 32:
        return np.uint32
    elif nbits == 8:
        return np.uint8
    else:
        return np.uint16


def update_axes_from_meta(
    meta_file: DectrisMetafile,
    axes_list: List[Axis],
    osc_axis: str | None = None,
    use_config: bool = False,
):
    """Update goniometer or detector axes values from those stores in the _dectris group.

    Args:
        meta_file (DectrisMetafile): Handle to Dectris-shaped meta.h5 file.
        axes_list (List[Axis]): List of axes to look up and eventually update.
        osc_axis (str | None, optional): If passed, the number of images corresponding to the osc_axis \
            will be updated too. Defaults to None.
        use_config (bool, optional): If passed read from config dataset in meta file instead of _dectris\
            group. Defaults to False.
    """
    overwrite_logger.debug("Updating axes list with values saved to _dectris group.")
    if meta_file.hasDectrisGroup is False:
        overwrite_logger.warning(
            "No Dectris group in meta file. No values will be updated."
        )
        return

    if use_config is True and meta_file.hasConfig is True:
        config = meta_file.read_config_dset()
    else:
        config = meta_file.read_dectris_config()
    num = meta_file.get_full_number_of_images()

    for ax in axes_list:
        if f"{ax.name}_start" in config.keys():
            ax.start_pos = config[f"{ax.name}_start"]
            overwrite_logger.debug(f"Start value for axis {ax.name}: {ax.start_pos}.")
            if f"{ax.name}_increment" in config.keys():
                ax.increment = config[f"{ax.name}_increment"]
                overwrite_logger.debug(
                    f"Increment value for axis {ax.name}: {ax.increment}."
                )
        if osc_axis and ax.name == osc_axis:
            ax.num_steps = num

        if ax.name == "det_z":
            dist = units_of_length(meta_file.get_detector_distance())
            ax.start_pos = dist.to("mm").magnitude
            overwrite_logger.debug(f"Start value for axis {ax.name}: {ax.start_pos}.")
