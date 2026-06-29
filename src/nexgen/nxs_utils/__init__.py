from __future__ import annotations

from pydantic.dataclasses import dataclass

from .axes import Axis, TransformationType
from .detector import (
    CetaDetector,
    Detector,
    DetectorModule,
    DetectorType,
    EigerDetector,
    JungfrauDetector,
    SinglaDetector,
    TristanDetector,
    TVIPSDetector,
)
from .goniometer import Goniometer
from .sample import Sample
from .source import Attenuator, Beam, Facility, Source


@dataclass(config={"arbitrary_types_allowed": True})
class NxObjectsComposite:
    goniometer: Goniometer
    detector: Detector
    source: Source
    beam: Beam
    attenuator: Attenuator
    sample: Sample | None


__all__ = [
    "Axis",
    "Goniometer",
    "Detector",
    "DetectorModule",
    "DetectorType",
    "SinglaDetector",
    "TristanDetector",
    "EigerDetector",
    "JungfrauDetector",
    "SinglaDetector",
    "Source",
    "Beam",
    "Attenuator",
    "Sample",
    "TransformationType",
    "Facility",
    "CetaDetector",
    "TVIPSDetector",
    "NxObjectsComposite",
]
