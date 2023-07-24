"""
Define and store basic beamline utilities.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from dataclasses_json import DataClassJsonMixin

from nexgen.nxs_utils import (
    Attenuator,
    Axis,
    Beam,
    Detector,
    Source,
    TransformationType,
)
from nexgen.utils import Point3D


@dataclass
class PumpProbe(DataClassJsonMixin):
    """
    Define pump probe parameters.

    Args:
        pump_status (bool): Pump on/off
        pump_exposure (float, optional): Pump exposure time, in s.
        pump_delay (float, optional): Pump delay, in s.
        pump_repeat (int, optional): Repeat mode.
    """

    pump_status: bool = False
    pump_exposure: Optional[float] = None
    pump_delay: Optional[float] = None
    pump_repeat: Optional[int] = 0

    def __post_init__(self):
        if self.pump_exposure:
            self.pump_status = True


@dataclass
class BeamlineAxes:
    """Beamline specific axes for goniometer, detector and detector module."""

    gonio: List[Axis]
    det_axes: List[Axis]
    fast_axis: Point3D | Tuple[float, float, float]
    slow_axis: Point3D | Tuple[float, float, float]

    def __post_init__(self):
        if not isinstance(self.fast_axis, Point3D):
            self.fast_axis = Point3D(*self.fast_axis)
        if not isinstance(self.slow_axis, Point3D):
            self.slow_axis = Point3D(*self.slow_axis)


# I24
I24Eiger = BeamlineAxes(
    gonio=[
        Axis("omega", ".", TransformationType.ROTATION, (-1, 0, 0)),
        Axis("sam_z", "omega", TransformationType.TRANSLATION, (0, 0, 1)),
        Axis("sam_y", "sam_z", TransformationType.TRANSLATION, (0, 1, 0)),
        Axis("sam_x", "sam_y", TransformationType.TRANSLATION, (1, 0, 0)),
    ],
    det_axes=[Axis("det_z", ".", TransformationType.TRANSLATION, (0, 0, 1))],
    fast_axis=Point3D(-1, 0, 0),
    slow_axis=Point3D(0, -1, 0),
)

I24Jungfrau = BeamlineAxes(
    gonio=[
        Axis("omega", ".", TransformationType.ROTATION, (0, 1, 0)),
        Axis("sam_z", "omega", TransformationType.TRANSLATION, (0, 0, 1)),
        Axis("sam_y", "sam_z", TransformationType.TRANSLATION, (0, 1, 0)),
        Axis("sam_x", "sam_y", TransformationType.TRANSLATION, (1, 0, 0)),
    ],
    det_axes=[Axis("det_z", ".", TransformationType.TRANSLATION, (0, 0, 1))],
    fast_axis=Point3D(-1, 0, 0),
    slow_axis=Point3D(0, -1, 0),
)

# I19-2
I19_2_gonio = [
    Axis("omega", ".", TransformationType.ROTATION, (-1, 0, 0)),
    Axis("kappa", "omega", TransformationType.ROTATION, (-0.642788, -0.766044, 0)),
    Axis("phi", "kappa", TransformationType.ROTATION, (-1, 0, 0)),
    Axis("sam_z", "phi", TransformationType.TRANSLATION, (0, 0, 1)),
    Axis("sam_y", "sam_z", TransformationType.TRANSLATION, (0, 1, 0)),
    Axis("sam_x", "sam_y", TransformationType.TRANSLATION, (1, 0, 0)),
]

I19_2Eiger = BeamlineAxes(
    gonio=I19_2_gonio,
    det_axes=[
        Axis("two_theta", ".", TransformationType.ROTATION, (-1, 0, 0)),
        Axis("det_z", "two_theta", TransformationType.TRANSLATION, (0, 0, 1)),
    ],
    fast_axis=Point3D(0, 1, 0),
    slow_axis=Point3D(-1, 0, 0),
)

I19_2Tristan = BeamlineAxes(
    gonio=I19_2_gonio,
    det_axes=[
        Axis("two_theta", ".", TransformationType.ROTATION, (-1, 0, 0), 0),
        Axis("det_z", "two_theta", TransformationType.TRANSLATION, (0, 0, 1)),
    ],
    fast_axis=Point3D(-1, 0, 0),
    slow_axis=Point3D(0, 1, 0),
)


def collection_summary_log(
    logger: logging.Logger,
    gonio_axes: List[Axis],
    scan_axis: List[str],
    detector: Detector,
    attenuator: Attenuator,
    beam: Beam,
    source: Source,
    timestamps: Tuple[str],
):
    """General function to log a collection summary."""
    logger.info("--- COLLECTION SUMMARY ---")
    logger.info("Source information")
    logger.info(f"Facility: {source.name} - {source.facility_type}.")
    logger.info(f"Beamline: {source.beamline}")

    logger.info(f"Incident beam wavelength: {beam.wavelength}")
    logger.info(f"Attenuation: {attenuator.transmission}")

    logger.info(f"Scan axis/axes: {scan_axis}")

    logger.info("Goniometer information")
    for ax in gonio_axes:
        logger.info(
            f"Goniometer axis: {ax.name} => {ax.start_pos}, {ax.transformation_type} on {ax.depends}"
        )
    logger.info("Detector information")
    logger.info(f"Detector in use: {detector.detector_params.description}")
    logger.info(
        f"Sensor made of {detector.detector_params.sensor_material} x {detector.detector_params.sensor_thickness}"
    )
    logger.info(
        f"Detector is a {detector.detector_params.image_size[::-1]} array of {detector.detector_params.pixel_size} pixels"
    )
    for ax in detector.detector_axes:
        logger.info(
            f"Detector axis: {ax.name} => {ax.start_pos}, {ax.transformation_type} on {ax.depends}"
        )

    logger.info(f"Recorded beam center is: {detector.beam_center}.")
    logger.info(f"Recorded exposure time: {detector.exp_time} s.")

    logger.info(f"Timestamps recorded: {timestamps}")
