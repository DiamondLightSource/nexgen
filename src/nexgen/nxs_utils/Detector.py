"""
Object definition for detectors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Tuple, Union

from dataclasses_json import DataClassJsonMixin

from ..utils import Point3D
from .Axes import Axis


class UnknownDetectorTypeError(Exception):
    pass


EIGER_CONST = {
    "flatfield": "flatfield",
    "flatfield_applied": "_dectris/flatfield_correction_applied",
    "pixel_mask": "mask",
    "pixel_mask_applied": "_dectris/pixel_mask_applied",
    "bit_depth_readout": "_dectris/bit_depth_image",  # Gorilla to be consistent with NeXus format (and make DIALS work)
    "bit_depth_image": "_dectris/bit_depth_image",
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

JUNGFRAU_CONST = {
    "flatfield": None,
    "flatfield_applied": False,
    "pixel_mask": None,
    "pixel_mask_applied": False,
    "software_version": "0.0.0",
}

SINGLA_CONST = {
    "flatfield": None,
    "flatfield_applied": False,
    "pixel_mask": None,
    "pixel_mask_applied": False,
    "software_version": "0.0.0",
}


@dataclass
class EigerDetector(DataClassJsonMixin):
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

    @property
    def constants(self) -> Dict:
        return EIGER_CONST

    @property
    def hasMeta(self) -> bool:
        return True


@dataclass
class TristanDetector(DataClassJsonMixin):
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

    @property
    def constants(self) -> Dict:
        return TRISTAN_CONST

    @property
    def hasMeta(self) -> bool:
        return True


@dataclass
class SinglaDetector(DataClassJsonMixin):
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

    @property
    def constants(self) -> Dict:
        return SINGLA_CONST

    @property
    def hasMeta(self) -> bool:
        return False


@dataclass
class JungfrauDetector(DataClassJsonMixin):
    """Define a Dectris Jungfrau detector."""

    description: str
    image_size: List[float] | Tuple[float]
    sensor_material: str = "Si"
    sensor_thickness: str = "0.320mm"
    overload: int = 1000000
    underload: int = -10
    pixel_size: List[str | float] = field(
        default_factory=lambda: ["0.075mm", "0.075mm"]
    )
    detector_type: str = "Pixel"

    @property
    def constants(self) -> Dict:
        return JUNGFRAU_CONST

    @property
    def hasMeta(self) -> bool:
        return False


DetectorType = Union[EigerDetector, TristanDetector, SinglaDetector, JungfrauDetector]


@dataclass
class DetectorModule(DataClassJsonMixin):
    fast_axis: Tuple[float] | Point3D
    slow_axis: Tuple[float] | Point3D
    module_offset: str = "1"

    def __post_init__(self):
        if isinstance(self.fast_axis, Point3D):
            self.fast_axis = (self.fast_axis.x, self.fast_axis.y, self.fast_axis.z)
        if isinstance(self.slow_axis, Point3D):
            self.slow_axis = (self.slow_axis.x, self.slow_axis.y, self.slow_axis.z)


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
        self.module = DetectorModule(module_vectors[0], module_vectors[1])

    def __repr__(self) -> str:
        det_msg = (
            f"{self.detector_params.description} \n\t"
            f"Image size {self.detector_params.image_size} pixels of size {self.detector_params.pixel_size}; \n\t"
            f"{self.detector_params.sensor_material} sensor x {self.detector_params.sensor_thickness}; \n\t"
            "Detector axes: \n\t"
        )
        for ax in self.detector_axes:
            det_msg += f"{ax.name}: {ax.start_pos} => {ax.transformation_type.value} on {ax.depends} \n\t"
        det_msg += (
            "Detector module axes: \n\t"
            f"Fast axis: {self.module.fast_axis} \n\t Slow axis: {self.module.slow_axis}\n"
        )
        return f"Detector description: {det_msg}"

    def get_detector_description(self) -> str:
        """Get detector description string."""
        return self.detector_params.description

    def get_detector_mode(self) -> str:
        """Data type collected by the detector.
        If no mode specified in detector parameters, defaults to images.
        """
        if "mode" in self.detector_params.__dataclass_fields__:
            return self.detector_params.mode
        return "images"

    def get_module_info(self):
        """Write the module information to a dictionary."""
        return self.module.to_dict()
