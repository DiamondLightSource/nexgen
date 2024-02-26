"""
Define and store basic beamline utilities.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from dataclasses_json import DataClassJsonMixin

from nexgen.nxs_utils import Attenuator, Axis, Beam, Detector, Goniometer, Source
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


def collection_summary_log(
    logger: logging.Logger,
    goniometer: Goniometer,
    detector: Detector,
    attenuator: Attenuator,
    beam: Beam,
    source: Source,
    timestamps: Tuple[str],
):
    """General function to log a collection summary."""
    logger.info("--- COLLECTION SUMMARY ---")
    logger.info(source.__repr__())

    logger.info(f"Incident beam wavelength: {beam.wavelength}")
    logger.info(f"Attenuation: {attenuator.transmission}")

    logger.info(goniometer.__repr__())
    logger.info(detector.__repr__())

    logger.info(f"Recorded beam center is: {detector.beam_center}.")
    logger.info(f"Recorded exposure time: {detector.exp_time} s.")

    logger.info(f"Timestamps recorded: {timestamps}")
