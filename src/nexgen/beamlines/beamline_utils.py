"""
Define and store basic beamline utilities.
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence

from pydantic import BaseModel
from pydantic.dataclasses import dataclass

from nexgen.nxs_utils import Attenuator, Axis, Beam, Detector, Goniometer, Source
from nexgen.utils import Point3D


class GeneralParams(BaseModel):
    """Parameters passed as input from the beamline.

    Args:
        exposure_time (float): Exposure time, in s.
        beam_center (Sequence[float]): Beam center (x,y) position, in pixels.
        wavelength (float, optional): Incident beam wavelength, in A.
        transmission (float, optional): Attenuator transmission, in %.
        flux (float, optional): Total flux.
    """

    exposure_time: float
    beam_center: Sequence[float]
    wavelength: float
    transmission: Optional[float] = None
    flux: Optional[float] = None


class PumpProbe(BaseModel):
    """
    Define pump probe parameters for a serial experiment on I24.

    Args:
        pump_status (bool, optional): Pump probe on/off.
        pump_exposure (float, optional): Pump exposure time, in s.
        pump_delay (float, optional): Pump delay, in s.
        pump_repeat (int, optional): Repeat mode.
    """

    pump_status: Optional[bool] = False
    pump_exposure: Optional[float] = None
    pump_delay: Optional[float] = None
    pump_repeat: Optional[int] = 0


@dataclass
class BeamlineAxes:
    """Beamline specific axes for goniometer, detector and detector module."""

    gonio: list[Axis]
    det_axes: list[Axis]
    fast_axis: Point3D | tuple[float, float, float]
    slow_axis: Point3D | tuple[float, float, float]

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
    timestamps: tuple[str],
):
    """General function to log a collection summary."""
    logger.debug("--- COLLECTION SUMMARY ---")
    msg = f"Facility: {source.facility.name} - {source.facility.type}. \n\t"
    msg += f"Beamline / instrument: {source.beamline} \n\t"
    if source.probe:
        msg += f"Probe: {source.probe}"
    logger.debug(f"Source information: \n\t{msg}")

    logger.debug(f"Incident beam wavelength: {beam.wavelength}")
    logger.debug(f"Attenuation: {attenuator.transmission}")

    logger.debug(goniometer.__repr__())
    logger.debug(detector.__repr__())

    logger.debug(f"Recorded beam center is: {detector.beam_center}.")
    logger.debug(f"Recorded exposure time: {detector.exp_time} s.")

    logger.debug(f"Timestamps recorded: {timestamps}")
