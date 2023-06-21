from __future__ import annotations

from dataclasses import dataclass

from dataclasses_json import DataClassJsonMixin

from .Axes import Axis
from .Detector import Detector, EigerDetector, TristanDetector
from .Goniometer import Goniometer
from .Source import Attenuator, Beam, Source

__all__ = [
    "Axis",
    "Goniometer",
    "Detector",
    "TristanDetector",
    "EigerDetector",
    "Source",
    "Beam",
    "Attenuator",
]


@dataclass
class Sample(DataClassJsonMixin):
    name: str | None = None
    depends_on: str | None = None
    temperature: str | None = None
