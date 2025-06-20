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
    pressure: float | None = None

    def get_sample_info_as_dict(self) -> dict | None:
        """Write a dict with sample details that does not include depends on."""
        d = {k: v for k, v in self.__dict__.items() if v and k != "depends_on"}
        if len(d) == 0:
            return None
        return d
