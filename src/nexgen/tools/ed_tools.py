"""
Tools to extract metadata for Electron Diffraction.
"""

from __future__ import annotations

import logging
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Any

import h5py
import hdf5plugin  # noqa: F401
import numpy as np
from numpy.typing import ArrayLike

logger = logging.getLogger("nexgen.EDtools.Singla")
logger.setLevel(logging.DEBUG)


class SinglaMaster:
    """
    Describes a master file for a Dectris Singla detector.
    """

    @staticmethod
    def isDectrisSingla(filename):
        with h5py.File(filename, "r") as fh:
            description = fh["/entry/instrument/detector/description"][()]
        if b"SINGLA" in description.upper():
            return True
        return False

    def __init__(self, handle: h5py.File):
        self._handle = handle

    def __len__(self):
        return len(self._handle)

    def __str__(self):
        return f"File {self._handle.filename} opened in '{self._handle.mode}' mode."

    def __getitem__(self, key: str) -> h5py.Group | h5py.Dataset:
        return self._handle[key]

    @cached_property
    def walk(self) -> list[str]:
        obj_list = []
        self._handle.visit(obj_list.append)
        return obj_list

    def get_number_of_images(self) -> int:
        _loc = [obj for obj in self.walk if "nimages" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def get_number_of_triggers(self) -> int:
        _loc = [obj for obj in self.walk if "ntriggers" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def full_number_of_images(self) -> int:
        return self.get_number_of_images() * self.get_number_of_triggers()

    def get_trigger_mode(self) -> str:
        _loc = [obj for obj in self.walk if "trigger_mode" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def get_mask(self) -> tuple[bool, ArrayLike]:
        M = [obj for obj in self.walk if "pixel_mask" in obj]
        if len(M) > 0:
            mask_path = [_loc for _loc in M if _loc.split("/")[-1] == "pixel_mask"]
            mask_applied_path = [_loc for _loc in M if "applied" in _loc]
            mask_applied = (
                False
                if len(mask_applied_path) == 0
                else self.__getitem__(mask_applied_path[0])[()]
            )
            mask = None if len(mask_path) == 0 else self.__getitem__(mask_path[0])[()]
            return (mask_applied, mask)
        return (False, None)

    def get_flatfield(self) -> tuple[bool, ArrayLike]:
        F = [obj for obj in self.walk if "flatfield" in obj]
        if len(F) > 0:
            flatfield_path = [_loc for _loc in F if _loc.split("/")[-1] == "flatfield"]
            flatfield_applied_path = [_loc for _loc in F if "applied" in _loc]
            flatfield_applied = (
                False
                if len(flatfield_applied_path) == 0
                else self.__getitem__(flatfield_applied_path[0])[()]
            )
            flatfield = (
                None
                if len(flatfield_path) == 0
                else self.__getitem__(flatfield_path[0])[()]
            )
            return (flatfield_applied, flatfield)
        return (False, None)

    def get_bit_bepth_readout(self) -> int:
        _loc = [obj for obj in self.walk if "bit_depth_readout" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]  # type SCALAR

    def get_bit_bepth_image(self) -> int:
        _loc = [obj for obj in self.walk if "bit_depth_image" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def get_detector_number(self) -> str:
        _loc = [obj for obj in self.walk if "detector_number" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def get_detector_readout_time(self) -> float:
        _loc = [obj for obj in self.walk if "detector_readout_time" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def get_exposure_time(self) -> float:
        _loc = [obj for obj in self.walk if "count_time" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def get_photon_energy(self) -> float:
        _loc = [obj for obj in self.walk if "photon_energy" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def get_countrate_correction(self) -> int:
        _loc = [obj for obj in self.walk if "countrate_correction_applied" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def get_software_version(self) -> bytes:
        _loc = [obj for obj in self.walk if "software_version" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def get_data_collection_date(self) -> str:
        _loc = [obj for obj in self.walk if "data_collection_date" in obj]
        if len(_loc) == 0:
            return None
        else:
            collection_date = str(self.__getitem__(_loc[0])[()])[2:21]
            collection_date = datetime.strptime(collection_date, "%Y-%m-%dT%H:%M:%S")
            return collection_date


def extract_exposure_time_from_master(master: Path | str) -> float:
    """
    Extracts the exposure time from the count_time field in the master file.

    Args:
        master (Path | str): Path to Singla master file.

    Returns:
        exposure_time (float): Exposure time, in seconds.
    """

    if SinglaMaster.isDectrisSingla(master) is False:
        logger.warning(f"The file {master} is the wrong format.")
        return

    exposure_time = None

    with h5py.File(master, "r") as fh:
        singla = SinglaMaster(fh)
        exposure_time = singla.get_exposure_time()

    return exposure_time


def extract_start_time_from_master(master: Path | str) -> datetime:
    """
    Extracts start_time from the data_collection_date field of the master file.

    Args:
        master (Path | str): Path to Singla master file.

    Returns:
        start_time (datetime): Collection start time, as datetime object.
    """

    if SinglaMaster.isDectrisSingla(master) is False:
        logger.warning(f"The file {master} is the wrong format.")
        return

    start_time = None

    with h5py.File(master, "r") as fh:
        singla = SinglaMaster(fh)
        start_time = singla.get_data_collection_date()

    return start_time


def extract_detector_info_from_master(master: Path | str) -> dict[str, Any]:
    """
    Extracts mask, flatfield and any other information relative to the detector \
    from a Singla master file.

    Args:
        master (Path | str): Path to Singla master file.

    Returns:
        dict[str, Any]: Dictionary of information relative to the detector.
    """

    if SinglaMaster.isDectrisSingla(master) is False:
        logger.warning(f"The file {master} is the wrong format.")
        return

    D = {}
    with h5py.File(master, "r") as fh:
        singla = SinglaMaster(fh)
        MASK = singla.get_mask()
        if MASK[1] is not None:
            logger.info("Pixel_mask has been found in master file.")
        FF = singla.get_flatfield()
        if FF[1] is not None:
            logger.info("Flatfield has been found in master file.")
        D["pixel_mask"] = MASK[1]
        D["pixel_mask_applied"] = MASK[0]
        D["flatfield"] = FF[1]
        D["flatfield_applied"] = FF[0]
        D["software_version"] = singla.get_software_version()
        D["bit_depth_readout"] = singla.get_bit_bepth_readout()
        D["detector_number"] = singla.get_detector_number()
        D["detector_readout_time"] = singla.get_detector_readout_time()
        D["photon_energy"] = singla.get_photon_energy()

    return D


def centroid_max(image: ArrayLike) -> tuple[float, float]:
    """
    Find the centre of gravity of the maximum pixels.

    Args:
        image (ArrayLike): Pixel image.

    Returns:
        tuple[float, float]: Centroid (x,y) position.
    """

    y, x = np.where(image == np.amax(image))
    return np.mean(x), np.mean(y)


def find_beam_centre(
    master: Path | str, data: Path | str, data_entry_key: str = "/entry/data/data"
) -> tuple[float, float]:
    """
    Calculate the beam center position for Electron Diffraction data collected on Singla detector.

    Args:
        master (Path | str): Path to Singla master file.
        data (Path | str): Path to data file.
        data_entry_key (str, optional): Key for the location of the images inside the Singla data file. Defaults to "/entry/data/data".

    Returns:
        fast, slow (tuple[float, float]): Beam center position (fast, slow) on the detector. \
            None if the pixel_mask can't be found.
    """

    with h5py.File(master, "r") as fh:
        singla = SinglaMaster(fh)
        pixel_mask = singla.get_mask()[1]

    # If the module gap is unmasked we would get bad results
    if pixel_mask is None:
        return None

    # Set the ROI to be +/- 100 pixels around the image centre
    yc, xc = (e // 2 for e in pixel_mask.shape)
    x0 = xc - 100
    x1 = xc + 100
    y0 = yc - 100
    y1 = yc + 100

    # Bool selection for masked pixels in the ROI
    pixel_mask = pixel_mask[y0:y1, x0:x1] == 1

    images = []
    with h5py.File(data, "r") as fh:
        data = fh[data_entry_key]
        num_images = data.shape[0]
        for i in range(0, num_images, num_images // min(num_images, 10)):
            image = data[i, y0:y1, x0:x1]
            image[pixel_mask] = 0
            images.append(image)

    beam_centres = [centroid_max(im) for im in images]
    x, y = zip(*beam_centres)

    # For robustness against blank images, remove any value more than 5 px
    # from the median
    med_x = np.median(x)
    med_y = np.median(y)
    x = [e for e in x if abs(e - med_x) < 5]
    y = [e for e in y if abs(e - med_y) < 5]

    # Correct for offset of the ROI and shift to centre pixel
    fast = xc - 100 + np.mean(x) + 0.5
    slow = yc - 100 + np.mean(y) + 0.5

    return fast, slow
