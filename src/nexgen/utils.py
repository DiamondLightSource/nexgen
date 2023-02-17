from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Tuple

import pint

# Define coordinates
Point3D = namedtuple("Point3D", ("x", "y", "z"))
Point3D.__doc__ = """Coordinates in 3D space."""

# Define axes and scans
@dataclass
class Axis:
    name: str
    depends: str
    transformation_type: Literal["translation", "rotation"]
    vector: Point3D | Tuple[float, float, float]
    start_pos: float
    increment: float = 0.0
    offset: Point3D | Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def __post_init__(self):
        if type(self.vector) is Point3D:
            self.vector = (self.vector.x, self.vector.y, self.vector.z)
        if type(self.offset) is Point3D:
            self.offset = (self.offset.x, self.offset.y, self.offset.z)

    @property
    def unit(self) -> str:
        if self.transformation_type == "translation":
            return "mm"
        else:
            return "deg"

    @property
    def is_scan(self) -> bool:
        if self.increment != 0.0:
            return True
        return False


@dataclass
class ScanAxis:
    axis: Axis
    num_imgs: int
    snaked: bool = False  # only for grid scans
    order: int = 1  # whether it's the first, only relevant for grid scans

    @property
    def end_pos(self) -> float:
        return self.axis.start_pos + self.axis.increment * self.num_imgs

    def calculate_scan(self):
        pass


# Initialize registry and a Quantity constructor
ureg = pint.UnitRegistry()
Q_ = ureg.Quantity


def units_of_length(q: str | float, to_base: bool = False) -> Q_:  # -> pint.Quantity:
    """
    Check that a quantity of length is compatible with NX_LENGTH, defaulting to m if dimensionless.

    Args:
        q (Any): An object that can be interpreted as a pint Quantity, it can be dimensionless.
        to_base (bool, optional): If True, convert to base units of length (m). Defaults to False.

    Raises:
        ValueError: If the input value is a negative number.
        pint.errors.DimensionalityError: If the input value is not a quantity of lenght.

    Returns:
        quantity (pint.Quantity): A pint quantity with units applied if it was dimensionless.
    """
    quantity = Q_(q)
    if quantity <= 0:
        raise ValueError("Quantity (length) must be positive.")
    quantity = quantity * ureg.m if quantity.dimensionless else quantity
    if quantity.check("[length]"):
        if to_base is True:
            return quantity.to_base_units()
        else:
            return quantity
    else:
        raise pint.errors.DimensionalityError(
            quantity, "a quantity of", quantity.dimensionality, ureg.mm.dimensionality
        )


def units_of_time(q: str) -> Q_:  # -> pint.Quantity:
    """
    Check that a quantity of time is compatible with NX_TIME, defaulting to s if dimensionless.
    Convert to seconds if time is passed as a fraction of it.

    Args:
        q (str): A string that can be interpreted as a pint Quantity, it can be dimensionless.

    Raises:
        ValueError: If the input value is a negative number.
        pint.errors.DimensionalityError: If the input value is not a quantity of lenght.

    Returns:
        quantity (pint.Quantity): A pint quantity in s, with units applied if it was dimensionless.
    """
    quantity = Q_(q)
    if quantity <= 0:
        raise ValueError("Quantity (time) of time must be positive.")
    quantity = quantity * ureg.s if quantity.dimensionless else quantity
    if quantity.check("[time]"):
        return quantity.to_base_units()
    else:
        raise pint.errors.DimensionalityError(
            quantity, "a quantity of", quantity.dimensionality, ureg.s.dimensionality
        )


def get_iso_timestamp(ts: str | float) -> str:
    """
    Format a timestamp string to be stores in a NeXus file according to ISO8601: 'YY-MM-DDThh:mm:ssZ'

    Args:
        ts (str | float): Input string, can also be a timestamp (eg. time.time()) string.
                        Allowed formats: "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%a %b %d %Y %H:%M:%S", "%A, %d. %B %Y %I:%M%p".

    Returns:
        ts_iso (str): Formatted timestamp.
    """
    # Format strings for timestamps
    format_list = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%a %b %d %Y %H:%M:%S",
        "%A, %d. %B %Y %I:%M%p",
    ]
    if ts is None:
        return None
    try:
        ts = float(ts)
        ts_iso = datetime.utcfromtimestamp(ts).replace(microsecond=0).isoformat()
    except ValueError:
        for fmt in format_list:
            try:
                ts_iso = datetime.strptime(ts, fmt).isoformat()
            except ValueError:
                ts_iso = str(ts)
    if ts_iso.endswith("Z") is False:
        ts_iso += "Z"
    return ts_iso
