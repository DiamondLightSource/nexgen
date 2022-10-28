"""
Tools to extract metadata for Electron Diffraction.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import h5py
from numpy.typing import ArrayLike

try:
    # Only for Python version >= 3.8
    from functools import cached_property
except ImportError:
    # Compatibility for earlier Python versions
    import functools

    def cached_property(func):
        @property
        @functools.wraps(func)
        def wrapper_decorator(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper_decorator


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
    def walk(self) -> List[str]:
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

    def get_trigger_mode(self) -> str:
        _loc = [obj for obj in self.walk if "trigger_mode" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[()]

    def get_mask(self) -> Tuple[bool, ArrayLike]:
        M = [obj for obj in self.walk if "pixel_mask" in obj]
        if len(M) > 0:
            mask_path = [_loc for _loc in M if _loc.split("/")[-1] == "pixel_mask"]
            mask_applied_path = [_loc for _loc in M if "applied" in _loc]
            if len(mask_applied_path) == 0:
                return (None, self.__getitem__(mask_path[0])[()])
            if len(mask_path) == 0:
                return (self.__getitem__(mask_applied_path[0])[()], None)
            return (
                self.__getitem__(mask_applied_path[0])[()],
                self.__getitem__(mask_path[0])[()],
            )
        return (None, None)

    def get_flafield(self) -> Tuple[bool, ArrayLike]:
        F = [obj for obj in self.walk if "flatfield" in obj]
        if len(F) > 0:
            flatfield_path = [_loc for _loc in F if _loc.split("/")[-1] == "flatfield"]
            flatfield_applied_path = [_loc for _loc in F if "applied" in _loc]
            if len(flatfield_applied_path) == 0:
                return (None, self.__getitem__(flatfield_path[0])[()])
            if len(flatfield_path) == 0:
                return (self.__getitem__(flatfield_applied_path[0])[()], None)
            return (
                self.__getitem__(flatfield_applied_path[0])[()],
                self.__getitem__(flatfield_path[0])[()],
            )
        return (None, None)

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


def extract_from_SINGLA_master(master: Path | str) -> Dict[str, Any]:
    """
    Extracts mask, flatfield and any other information relative to the detector \
    from a Singla master file.

    Args:
        master (Path | str): Path to master file.

    Returns:
        Dict[str, Any]: Dictionary of information relative to the detector.
    """
    import logging

    logger = logging.getLogger("nexgen.EDtools.Singla")
    logger.setLevel(logging.DEBUG)

    if SinglaMaster.isDectrisSingla(master) is False:
        logger.warning(f"The file {master} is the wrong format.")
        return

    D = {}
    with h5py.File(master, "r") as fh:
        singla = SinglaMaster(fh)
        MASK = singla.get_mask()
        if MASK[1] is not None:
            logger.info("Pixel_mask has been found in master file.")
        FF = singla.get_flafield()
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
