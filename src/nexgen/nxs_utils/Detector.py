"""
Object definition for detectors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Tuple, Union

from dataclasses_json import dataclass_json

from ..utils import Point3D
from .Axes import Axis

__all__ = ["EigerDetector", "TristanDetector", "Detector"]


class UnknownDetectorTypeError(Exception):
    pass


EIGER_CONST = {
    "flatfield": "flatfield",
    "flatfield_applied": "_dectris/flatfield_correction_applied",
    "pixel_mask": "mask",
    "pixel_mask_applied": "_dectris/pixel_mask_applied",
    "bit_depth_readout": "_dectris/bit_depth_readout",
    "detector_readout_time": "_dectris/detector_readout_time",
    "threshold_energy": "_dectris/threshold_energy",
    "software_version": "_dectris/software_version",
    "serial_number": "_dectris/detector_number",
}

TRISTAN_CONST = {
    "flatfield": "Tristan10M_flat_field_coeff_with_Mo_17.479keV.h5",
    "flatfield_applied": False,
    "pixel_mask": "Tristan10M_mask_with_spec.h5",
    "pixel_mask_applied": False,
    "software_version": "1.1.3",
    "detector_tick": "1562.5ps",
    "detector_frequency": "6.4e+08Hz",
    "timeslice_rollover": 18,
}


@dataclass_json
@dataclass
class EigerDetector:
    """Define a Dectris Eiger detector."""

    description: str
    image_size: List[float] | Tuple[float]
    sensor_material: Literal["Si", "CdTe"]
    overload: int
    underload: int
    pixel_size: List[str | float] = field(
        default_factory=lambda: ["0.075mm", "0.075mm"]
    )
    detector_type: str = "Pixel"

    @property
    def sensor_thickness(self) -> str:
        if self.sensor_material == "Si":
            return "0.450mm"
        else:
            return "0.750mm"


@dataclass_json
@dataclass
class TristanDetector:
    """Define a Tristan detector."""

    description: str
    image_size: List[float] | Tuple[float]
    sensor_material: str = "Si"
    sensor_thickness: str = "0.5mm"
    pixel_size: List[str | float] = field(
        default_factory=lambda: ["5.5e-05m", "5.5e-05m"]
    )
    detector_type: str = "Pixel"
    mode: Literal["events", "images"] = "events"


@dataclass_json
@dataclass
class SinglaDetector:
    """Define a Dectris Singla detector."""

    description: str
    image_size: List[float] | Tuple[float]
    sensor_material: str = "Si"
    sensor_thickness: str = "0.450mm"
    overload: int = 199996
    underload: int = -1
    pixel_size: List[str | float] = field(
        default_factory=lambda: ["0.075mm", "0.075mm"]
    )
    detector_type: str = "HPC"


DetectorType = Union[EigerDetector, TristanDetector, SinglaDetector]


class Detector:
    """Detector definition."""

    def __init__(
        self,
        detector_params: DetectorType,
        detector_axes: List[Axis],
        beam_center: List[float],
        exposure_time: float,
        module_vectors: List[Point3D] | List[Tuple],
    ):
        self.detector_params = detector_params
        self.detector_axes = detector_axes
        self.beam_center = beam_center
        self.exp_time = exposure_time
        if type(module_vectors[0]) is Point3D:
            self.fast_axis = module_vectors[0]
        else:
            self.fast_axis = Point3D(*module_vectors[0])
        if type(module_vectors[1]) is Point3D:
            self.slow_axis = module_vectors[1]
        else:
            self.slow_axis = Point3D(*module_vectors[1])

    def __repr__(self) -> str:
        det_msg = (
            f"{self.detector_params.description} \n\t"
            f"Image size {self.detector_params.image_size} pixels; \n\t"
            f"{self.detector_params.sensor_material} sensor x {self.detector_params.sensor_thickness}; \n"
            "Detector axes: \n\t"
        )
        for ax in self.detector_axes:
            det_msg += f"{ax.name}: {ax.start_pos} => {ax.transformation_type} on {ax.depends} \n\t"
        return f"Detector description: {det_msg}"

    def _generate_detector_dict(self):
        detector = self.detector_params.__dict__
        detector["axes"] = [ax.name for ax in self.detector_axes]
        detector["depends"] = [ax.depends for ax in self.detector_axes]
        detector["vectors"] = [ax.vector for ax in self.detector_axes]
        detector["starts"] = [ax.start_pos for ax in self.detector_axes]
        detector["units"] = [ax.units for ax in self.detector_axes]
        detector["types"] = [ax.transformation_type for ax in self.detector_axes]
        if "eiger" in self.detector_params.description.lower():
            detector["sensor_thickness"] = self.detector_params.sensor_thickness
            detector["mode"] = "images"
            detector.update(EIGER_CONST)
        elif "tristan" in self.detector_params.description.lower():
            # Mode is already in params
            detector.update(TRISTAN_CONST)
        else:
            raise UnknownDetectorTypeError("Unknown detector.")
        detector["beam_center"] = self.beam_center
        detector["exposure_time"] = self.exp_time
        return detector

    def _generate_module_dict(self):
        module = {
            "module_offset": "1",
            "fast_axis": [self.fast_axis.x, self.fast_axis.y, self.fast_axis.z],
            "slow_axis": [self.slow_axis.x, self.slow_axis.y, self.slow_axis.z],
        }
        return module

    def get_detector_description(self) -> str:
        return self.detector_params.description

    def to_dict(self):
        """Write the detector information to a dictionary."""
        return self._generate_detector_dict()

    def to_module_dict(self):
        """Write the module information to a dictionary."""
        return self._generate_module_dict()
