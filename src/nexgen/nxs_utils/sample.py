"""
Sample definition utilities.
"""

from __future__ import annotations

from pydantic.dataclasses import dataclass


@dataclass
class Sample:
    name: str | None = None
    depends_on: str | None = None
    temperature: float | None = None

    def to_dict(self) -> dict:
        return self.__dict__
