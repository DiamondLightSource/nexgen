"""
Object definition for Source, Beam and Attenuator
"""

from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass

from dataclasses_json import DataClassJsonMixin

# Describe facility
Facility = namedtuple("Facility", ("name", "short_name", "type", "id"))
Facility.__doc__ = """Facility description"""


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
        msg = f"Facility: {self.name} - {self.facility_type}. \n\t"
        msg += f"Beamline / instrument: {self.beamline} \n\t"
        if self.probe:
            msg += "Probe: {}"
        return f"Source information: \n\t{msg}"

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
            return f"{facility_id} BEAMLINE {self.beamline}"

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


@dataclass
class Beam(DataClassJsonMixin):
    """Beam definition."""

    wavelength: float
    flux: float | None = None


@dataclass
class Attenuator(DataClassJsonMixin):
    """Attenuator definition."""

    transmission: float
