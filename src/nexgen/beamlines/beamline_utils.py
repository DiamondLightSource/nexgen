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
    Define pump probe parameters for a serial experiment on I24.

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
    logger.debug("--- COLLECTION SUMMARY ---")
    logger.debug(source.__repr__())

    logger.debug(f"Incident beam wavelength: {beam.wavelength}")
    logger.debug(f"Attenuation: {attenuator.transmission}")

    logger.debug(goniometer.__repr__())
    logger.debug(detector.__repr__())

    logger.debug(f"Recorded beam center is: {detector.beam_center}.")
    logger.debug(f"Recorded exposure time: {detector.exp_time} s.")

    logger.debug(f"Timestamps recorded: {timestamps}")
