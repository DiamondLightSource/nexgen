"""
Utilities for axes definition
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from ..utils import Point3D


class TransformationType(Enum):
    ROTATION = "rotation"
    TRANSLATION = "translation"


# Define axes and scans
@dataclass
class Axis:
    """
    Define an axis object for goniometer or detector.
    """

    name: str
    depends: str
    transformation_type: TransformationType
    vector: Point3D | Tuple[float, float, float]
    start_pos: float = 0.0
    increment: float = 0.0
    num_steps: int = 0
    offset: Point3D | Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def __post_init__(self):
        if type(self.vector) is Point3D:
            self.vector = (self.vector.x, self.vector.y, self.vector.z)
        if type(self.offset) is Point3D:
            self.offset = (self.offset.x, self.offset.y, self.offset.z)
        self.transformation_type = self.transformation_type.value

    @property
    def units(self) -> str:
        if self.transformation_type == "translation":
            return "mm"
        else:
            return "deg"

    @property
    def end_pos(self) -> float:
        # Using the same system as scanspec
        return self.start_pos + self.increment * (self.num_steps - 1)

    @property
    def is_scan(self) -> bool:
        if self.increment != 0.0:
            return True
        return False
