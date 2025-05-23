"""
Utilities for axes definition
"""

from __future__ import annotations

from enum import StrEnum

from pydantic.dataclasses import dataclass

from ..utils import Point3D


class TransformationType(StrEnum):
    """Define axis transformation type
    - ROTATION
    - TRANSLATION
    """

    ROTATION = "rotation"
    TRANSLATION = "translation"


# Define axes and scans
@dataclass
class Axis:
    """
    Define an axis object for goniometer or detector.

    Attributes:
        name (str): Axis name.
        depends (str): Name of the axis it depends on.
        transformation_type (TransformationType): Rotation or translation.
        vector (Point3D | tuple): Axis vector.
        start_pos (float, optional): Start position of axis. Defaults to 0.0.
        increment (float, optional): Scan step size if the axis moves. Defaults to 0.0.
        num_steps (int, optional): Number of scan points. Defaults to 0.0.
        offset (Point3D | tuple, optional): Axis offset. Defaults to (0.0, 0.0, 0.0).

    Properties:
        units (str): Defined depending on transformation type: deg or mm.
        end_pos (float): Last point recorded in a scan colletion. Calculated from start_pos, increment and num_steps, 1-indexed.
        is_scan (bool): Whether axis is a scan axis.
    """

    name: str
    depends: str
    transformation_type: TransformationType
    vector: Point3D | tuple[float, float, float]
    start_pos: float = 0.0
    increment: float = 0.0
    num_steps: int = 0
    offset: Point3D | tuple[float, float, float] = (0.0, 0.0, 0.0)

    def __post_init__(self):
        if type(self.vector) is Point3D:
            self.vector = (self.vector.x, self.vector.y, self.vector.z)
        if type(self.offset) is Point3D:
            self.offset = (self.offset.x, self.offset.y, self.offset.z)

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
