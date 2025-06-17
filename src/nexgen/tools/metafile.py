"""
Define a Metafile object to describe the _meta.h5 file and get the necessary information from it.
"""

from __future__ import annotations

import re
from functools import cached_property

import h5py

__all__ = ["Metafile", "DectrisMetafile", "TristanMetafile"]

tristan_pattern = re.compile(r"ts_qty_module\d{2}")


class Metafile:
    def __init__(self, handle: h5py.File):
        self._handle = handle

    def __getitem__(self, key: str) -> h5py.Group | h5py.Dataset:
        return self._handle[key]

    def __len__(self):
        return len(self._handle)

    def __str__(self):
        return f"File {self._handle.filename} opened in '{self._handle.mode}' mode."

    @cached_property
    def walk(self) -> list[str]:
        obj_list = []
        self._handle.visit(obj_list.append)
        return obj_list

    @cached_property
    def hasMask(self):
        if "mask" in self.walk:
            return True
        return False

    @cached_property
    def hasFlatfield(self):
        if "flatfield" in self.walk:
            return True
        return False


class DectrisMetafile(Metafile):
    """
    Describes a _meta.h5 file for a Dectris Eiger detector.
    """

    def __init__(self, handle: h5py.File):
        super().__init__(handle)

    @cached_property
    def hasDectrisGroup(self) -> bool:
        if "_dectris" in self._handle.keys() and isinstance(
            self._handle["_dectris"], h5py.Group
        ):
            return True
        return False

    @cached_property
    def hasConfig(self) -> bool:
        if "config" in self._handle.keys():
            return True
        return False

    def read_dectris_config(self) -> dict:
        config = {}
        for k, v in self._handle["_dectris"].items():
            v = v[()]
            if len(v) == 1:
                v = v[0]
                if isinstance(v, bytes):
                    v = v.decode()
            config[k] = v
        return config

    def read_config_dset(self) -> dict:
        config = eval(self._handle["config"][()])
        return config

    def get_number_of_images(self) -> int:
        if self.hasDectrisGroup:
            config = self.read_dectris_config()
            return config["nimages"]
        else:
            _loc = [obj for obj in self.walk if "nimages" in obj]
            return self.__getitem__(_loc[0])[0]

    def get_number_of_triggers(self) -> int:
        if self.hasDectrisGroup:
            config = self.read_dectris_config()
            return config["ntrigger"]
        else:
            _loc = [obj for obj in self.walk if "ntrigger" in obj]
            return self.__getitem__(_loc[0])[0]

    def get_full_number_of_images(self) -> int:
        return self.get_number_of_triggers() * self.get_number_of_images()

    def get_detector_size(self) -> tuple:
        # NB. returns (fast, slow) but data_size in nxs file shoud be recorded (slow, fast)
        # => det_size[::-1]
        _loc = [obj for obj in self.walk if "pixels_in_detector" in obj]
        det_size = []
        for i in _loc:
            det_size.append(self.__getitem__(i)[0])
        if len(det_size) == 0:
            return None
        return tuple(det_size[::-1])

    def get_pixel_size(self) -> list:
        _loc = [obj for obj in self.walk if "pixel_size" in obj]
        pix = []
        for i in _loc:
            pix.append(self.__getitem__(i)[0])
        if len(pix) == 0:
            return None
        return pix

    def get_beam_center(self) -> list:
        _loc = [obj for obj in self.walk if "beam_center" in obj]
        bc = []
        for i in _loc:
            bc.append(self.__getitem__(i)[0])
        if len(bc) == 0:
            return None
        return bc

    def get_wavelength(self) -> float:
        _loc = [obj for obj in self.walk if "wavelength" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[0]

    def get_detector_distance(self) -> float:
        # Distance in Dectris meta file is in m.
        _loc = [obj for obj in self.walk if "detector_distance" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[0]

    def get_saturation_value(self) -> float:
        _loc = [obj for obj in self.walk if "countrate_correction_count_cutoff" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[0]

    def get_sensor_information(self) -> tuple[bytes, float]:
        _loc_material = [obj for obj in self.walk if "sensor_material" in obj]
        _loc_thickness = [obj for obj in self.walk if "sensor_thickness" in obj]
        return (
            self.__getitem__(_loc_material[0])[0],
            self.__getitem__(_loc_thickness[0])[0],
        )

    def get_bit_depth_image(self) -> int:
        _loc = [obj for obj in self.walk if "bit_depth_image" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[0]

    def get_data_collection_date(self) -> str:
        if self.hasDectrisGroup:
            config = self.read_dectris_config()
            return config["data_collection_date"]
        if self.hasConfig:
            config = self.read_config_dset()
            return config["data_collection_date"]
        _loc = [obj for obj in self.walk if "data_collection_date" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[0]

    def get_fw_version(self) -> str:
        if self.hasDectrisGroup:
            config = self.read_dectris_config()
            return config["eiger_fw_version"]
        if self.hasConfig:
            config = self.read_config_dset()
            return config["eiger_fw_version"]
        _loc = [obj for obj in self.walk if "eiger_fw_version" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[0]

    def get_serial_number(self) -> str:
        # Stored in meta file as "detector_number"
        if self.hasDectrisGroup:
            config = self.read_dectris_config()
            return config["detector_number"]
        if self.hasConfig:
            config = self.read_config_dset()
            return config["detector_number"]
        _loc = [obj for obj in self.walk if "detector_number" in obj]
        if len(_loc) == 0:
            return None
        return self.__getitem__(_loc[0])[0]

    def find_mask(self) -> tuple[str, str]:
        if self.hasMask:
            mask_path = [obj for obj in self.walk if obj.lower() == "mask"]
            mask_applied_path = [obj for obj in self.walk if "mask_applied" in obj]
            if len(mask_applied_path) == 0:
                return (mask_path[0], None)
            return (mask_path[0], mask_applied_path[0])
        return (None, None)

    def find_flatfield(self) -> tuple[str, str]:
        if self.hasFlatfield:
            flatfield_path = [obj for obj in self.walk if obj.lower() == "flatfield"]
            flatfield_applied_path = [
                obj for obj in self.walk if "flatfield_correction_applied" in obj
            ]
            if len(flatfield_applied_path) == 0:
                return (flatfield_path[0], None)
            return (flatfield_path[0], flatfield_applied_path[0])
        return (None, None)

    def find_software_version(self) -> str:
        _loc = [obj for obj in self.walk if "software_version" in obj]
        if len(_loc) == 0:
            return None
        return _loc[0]

    def find_threshold_energy(self) -> str:
        _loc = [obj for obj in self.walk if "threshold_energy" in obj]
        if len(_loc) == 0:
            return None
        return _loc[0]

    def find_bit_depth_readout(self) -> str:
        _loc = [obj for obj in self.walk if "bit_depth_readout" in obj]
        if len(_loc) == 0:
            return None
        return _loc[0]

    def find_bit_depth_image(self) -> str:
        _loc = [obj for obj in self.walk if "bit_depth_image" in obj]
        if len(_loc) == 0:
            return None
        return _loc[0]

    def find_detector_number(self) -> str:
        _loc = [obj for obj in self.walk if "detector_number" in obj]
        if len(_loc) == 0:
            return None
        return _loc[0]

    def find_detector_readout_time(self) -> str:
        _loc = [obj for obj in self.walk if "detector_readout_time" in obj]
        if len(_loc) == 0:
            return None
        return _loc[0]


class TristanMetafile(Metafile):
    """
    Describes a _meta.h5 file for a Tristan detector.
    """

    @staticmethod
    def isTristan(filename):
        with h5py.File(filename, "r") as fh:
            res = [k for k in fh.keys() if tristan_pattern.fullmatch(k)]
        if len(res) > 0:
            return True
        return False

    def __init__(self, handle: h5py.File):
        super().__init__(handle)

    def find_number_of_modules(self) -> int:
        n_modules = [k for k in self._handle.keys() if tristan_pattern.fullmatch(k)]
        return len(n_modules)

    def find_software_version(self) -> str:
        _loc = [obj for obj in self.walk if "software_version" in obj]
        if len(_loc) == 0:
            return None
        return _loc[0]

    def find_meta_version(self) -> str:
        _loc = [obj for obj in self.walk if "meta_version" in obj]
        if len(_loc) == 0:
            return None
        return _loc[0]
