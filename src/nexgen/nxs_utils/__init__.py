from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass

from dataclasses_json import dataclass_json

# Define coordinates
Point3D = namedtuple("Point3D", ("x", "y", "z"))
Point3D.__doc__ = """Coordinates in 3D space."""

# Describe facility
Facility = namedtuple("Facility", ("name", "short_name", "type", "id"))
Facility.__doc__ = """Facility description"""


@dataclass_json
@dataclass
class Sample:
    name: str | None = None
    depends_on: str | None = None
    temperature: str | None = None
