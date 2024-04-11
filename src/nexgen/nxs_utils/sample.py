"""
Sample definition utilities.
"""

from __future__ import annotations

from dataclasses import dataclass

from dataclasses_json import DataClassJsonMixin


@dataclass
class Sample(DataClassJsonMixin):
    name: str | None = None
    depends_on: str | None = None
    temperature: str | None = None
