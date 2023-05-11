"""
Object definition for Source, Beam and Attenuator
"""
from __future__ import annotations

from dataclasses import dataclass

from dataclasses_json import dataclass_json

from ..utils import Facility


class Source:
    """Source definition."""

    def __init__(
        self,
        beamline: str,
        facility: Facility = Facility(
            "Diamond Light Source",
            "DLS",
            "Synchrotron X-ray Source",
            None,
        ),
        probe: str | None = None,
    ):
        self.beamline = beamline

        self.name = facility.name
        self.short_name = facility.short_name
        self.facility_type = facility.type
        self.facility_id = facility.id

        self.probe = probe

    def __repr__(self) -> str:
        msg = f"Beamline {self.beamline} at {self.name}.\n"
        if self.probe:
            msg += "Probe: {}"
        return msg

    def set_instrument_name(self) -> str:
        """Set the instrument name from the details saved in source.

        If source type is not defined a priori, the function will assume it is a Synchrotron.
        If the facility_id is defined inside the source dictionary, that is the value that will be used.
        Naming tries to follow the recommended convention for NXmx:
        https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_diffrn_source.type.html

        Returns:
            name (str): The name to write under '/entry/instrument/name'
        """
        facility_id = "DIAMOND" if self.facility_id is None else self.facility_id

        if (
            self.facility_type is None
            or "SYNCHROTRON" not in self.facility_type.upper()
        ):
            return f"{facility_id} {self.beamline}"
        else:
            return self.name

    def _generate_source_dict(self):
        source = {
            "name": self.name,
            "type": self.facility_type,
            "short_name": self.short_name,
            "beamline_name": self.beamline,
        }
        if self.probe:
            source["probe"] = self.probe
        if self.facility_id:
            source["facility_id"] = self.facility_id
        return source

    def to_dict(self):
        """Write source information to a dictionary."""
        return self._generate_source_dict()


@dataclass_json
@dataclass
class Beam:
    """Beam definition."""

    wavelength: float
    flux: float | None = None


@dataclass_json
@dataclass
class Attenuator:
    """Attenuator definition."""

    transmission: float
