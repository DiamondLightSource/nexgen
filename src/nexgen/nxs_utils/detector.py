"""
Object definition for detectors.
"""

from __future__ import annotations

from typing import Literal, Union

from pydantic.dataclasses import Field, dataclass

from ..utils import Point3D
from .axes import Axis


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
    "photon_energy": "_dectris/photon_energy",
    "software_version": "_dectris/software_version",
    "ntrigger": "/_dectris/ntrigger",
    # "serial_number": "/_dectris/detector_number",
    # "eiger_fw_version": "/_dectris/eiger_fw_version",
    # "data_collection_date": "/_dectris/data_collection_date",
}

TRISTAN_CONST = {
    "flatfield": "Tristan10M_flat_field_coff_gap_filled_1_with_Mo_17.479keV.h5",  # "Tristan10M_flat_field_coeff_with_Mo_17.479keV.h5",
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

CETA_CONST = {
    "flatfield": None,
    "flatfield_applied": False,
    "pixel_mask": None,
    "pixel_mask_applied": False,
    "software_version": "0.0.0",
}

TVIPS_CONST = {
    "flatfield": None,
    "flatfield_applied": False,
    "pixel_mask": None,
    "pixel_mask_applied": False,
    "software_version": "0.0.0",
}


@dataclass
class TVIPSDetector:
    """Define a TVIPS camera"""

    description: str
    image_size: list[float] | tuple[float]
    pixel_size: str = "0.0155000mm"
    sensor_material: str = "Si"
    sensor_thickness: str = "0.0000000000001mm"
    detector_type: str = "CMOS"
    overload: int = 65534
    underload: int = 0

    @property
    def constants(self) -> dict:
        return TVIPS_CONST

    @property
    def hasMeta(self) -> bool:
        return False


@dataclass
class EigerDetector:
    """Define a Dectris Eiger detector.

    Attributes:
        description (str): Detector description.
        image_size (list | tuple): Dimensions in pixels, passed in the order (slow, fast) axis.
        sensor_material (str): Either Si or CdTe, on the material depends the sensor_thickness.
        overload (int): Saturation value for the detector, data is invalid above this value.
        underload (int): Lowest value measurable for the detector, data is invalid below this value.
        pixel_size (list[str], optional): Size of each detector pixel in both directions, order should be (x, y). Defaults to a pixel size of ['0.075mm', '0.075mm']
        detector_type (str, optional): Description of type of detector. Defaults to 'Pixel'.

    Properties:
        sensor_thickness (str): Defined depending on the sensor material: 0.450mm for Si, 0.750mm CdTe.
        constants (Dict): Dictionary of meta file locations to create the external links to fields such as pixel_mask, flatfield and bit_depth_readout.
    """

    description: str
    image_size: list[int] | tuple[int, int]
    sensor_material: Literal["Si", "CdTe"]
    overload: int
    underload: int
    pixel_size: list[str | float] = Field(
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
    def constants(self) -> dict:
        return EIGER_CONST

    @property
    def hasMeta(self) -> bool:
        return True


@dataclass
class TristanDetector:
    """Define a Tristan detector.

    Attributes:
        description (str): Detector description.
        image_size (list | tuple): Dimensions in pixels, passed in the order (slow, fast) axis.
        sensor_material (str): Sensor material. Defaults to Si.
        sensor_thickness (str): Sensor thickness. Defaults to 0.5mm
        pixel_size (list[str], optional): Size of each detector pixel in both directions, order should be (x, y). Defaults to a pixel size of ['5.5e-05m', '5.5e-05m']
        detector_type (str, optional): Description of type of detector. Defaults to 'Pixel'.
        mode (str): Acquisition mode for Tristan, either images or events. Defaults to events.

    Properties:
        constants (Dict): Detector specific constants, such as locations of pixel_mask and flatfield files, and detector tick, frequency and timeslice rollover for event mode.
    """

    description: str
    image_size: list[int] | tuple[int, int]
    sensor_material: str = "Si"
    sensor_thickness: str = "0.5mm"
    pixel_size: list[str | float] = Field(
        default_factory=lambda: ["5.5e-05m", "5.5e-05m"]
    )
    detector_type: str = "Pixel"
    mode: Literal["events", "images"] = "events"

    @property
    def constants(self) -> dict:
        return TRISTAN_CONST

    @property
    def hasMeta(self) -> bool:
        return True


@dataclass
class CetaDetector:
    """Define a Ceta-D detector."""

    description: str
    image_size: list[float] | tuple[float]
    pixel_size: list[str | float] = Field(
        default_factory=lambda: ["0.014mm", "0.014mm"]
    )
    sensor_material: str = "Si"
    sensor_thickness: str = "0.014mm"
    detector_type: str = "CMOS"
    overload: int = 1000000
    underload: int = -1000

    @property
    def constants(self) -> dict:
        return CETA_CONST

    @property
    def hasMeta(self) -> bool:
        return False


@dataclass
class SinglaDetector:
    """Define a Dectris Singla detector.

    Attributes:
        description (str): Detector description.
        image_size (list | tuple): Dimensions in pixels, passed in the order (slow, fast) axis.
        sensor_material (str): Sensor material. Defaults to Si.
        sensor_thickness (str): Sensor thickness. Defaults to 0.450mm
        overload (int): Saturation value for the detector, data is invalid above this value. Defaults to 199996.
        underload (int): Lowest value measurable for the detector, data is invalid below this value. Defaults to -1.
        pixel_size (list[str], optional): Size of each detector pixel in both directions, order should be (x, y). Defaults to a pixel size of ['0.075mm', '0.075mm']
        detector_type (str, optional): Description of type of detector. Defaults to 'HPC'.

    Properties:
        constants (Dict): Dictionary of meta file locations to create the external links to fields such as pixel_mask, flatfield and bit_depth_readout.
    """

    description: str
    image_size: list[int] | tuple[int, int]
    sensor_material: str = "Si"
    sensor_thickness: str = "0.450mm"
    overload: int = 199996
    underload: int = -1
    pixel_size: list[str | float] = Field(
        default_factory=lambda: ["0.075mm", "0.075mm"]
    )
    detector_type: str = "HPC"

    @property
    def constants(self) -> dict:
        return SINGLA_CONST

    @property
    def hasMeta(self) -> bool:
        return False


@dataclass
class JungfrauDetector:
    """Define a Dectris Jungfrau detector.

    Attributes:
        description (str): Detector description.
        image_size (list | tuple): Dimensions in pixels, passed in the order (slow, fast) axis.
        sensor_material (str): Sensor material. Defaults to Si.
        sensor_thickness (str): Sensor thickness. Defaults to 0.320mm
        overload (int): Saturation value for the detector, data is invalid above this value. Defaults to 1000000.
        underload (int): Lowest value measurable for the detector, data is invalid below this value. Defaults to -10.
        pixel_size (list[str], optional): Size of each detector pixel in both directions, order should be (x, y). Defaults to a pixel size of ['0.075mm', '0.075mm']
        detector_type (str, optional): Description of type of detector. Defaults to 'Pixel'.

    Properties:
        constants (Dict): Dictionary of meta file locations to create the external links to fields such as pixel_mask, flatfield and bit_depth_readout.
    """

    description: str
    image_size: list[int] | tuple[int, int]
    sensor_material: str = "Si"
    sensor_thickness: str = "0.320mm"
    overload: int = 1000000
    underload: int = -10
    pixel_size: list[str | float] = Field(
        default_factory=lambda: ["0.075mm", "0.075mm"]
    )
    detector_type: str = "Pixel"

    @property
    def constants(self) -> dict:
        return JUNGFRAU_CONST

    @property
    def hasMeta(self) -> bool:
        return False


DetectorType = Union[
    EigerDetector, TristanDetector, SinglaDetector, JungfrauDetector, CetaDetector
]


@dataclass
class DetectorModule:
    """A class to define the axes of a detector module.

    Attributes:
        fast_axis (tuple | Point3D): Vector defining the fast_axis direction.
        slow_axis (tuple | Point3D): Vector defining the slow_axis direction.
    """

    fast_axis: tuple[float, float, float] | Point3D
    slow_axis: tuple[float, float, float] | Point3D
    module_offset: str = "1"

    def __post_init__(self):
        if isinstance(self.fast_axis, Point3D):
            self.fast_axis = (self.fast_axis.x, self.fast_axis.y, self.fast_axis.z)
        if isinstance(self.slow_axis, Point3D):
            self.slow_axis = (self.slow_axis.x, self.slow_axis.y, self.slow_axis.z)


class Detector:
    """Detector definition.

    Attributes:
        detector_params: The detector parameters, unique to each detector type.
        detector_axes: The axes where the detector lays, their start positions and vectors in mcstas coordinates.
        beam_center: The beam center position, in pixels.
        exp_time: The collection exposure time, in seconds.
        module: The detector module definition, with fast_axis and slow_axis directions, in mcstas.
    """

    def __init__(
        self,
        detector_params: DetectorType,
        detector_axes: list[Axis],
        beam_center: list[float],
        exposure_time: float,
        module_vectors: list[Point3D] | list[tuple[float, float, float]],
    ):
        """
        Args:
            detector_params (DetectorType): Specific parameters relative to detector in use eg. TristanDetector("Tristan", [100, 200])
            detector_axes (list[Axes]): list of detector axes.
            beam_center (list[float]): Beam center position, in pixels.
            exposure_time (float): Exposure time of each image/collection, in s.
            module_vectors (list): list of detector module vectors in the order: (fast_axis, slow_axis).
        """
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
        return self.module.__dict__
