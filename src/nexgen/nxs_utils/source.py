"""
Object definition for Source, Beam and Attenuator
"""

from __future__ import annotations

from typing import NamedTuple

from pydantic.dataclasses import dataclass


# Describe facility
class Facility(NamedTuple):
    """Facility description."""

    name: str
    short_name: str
    type: str
    id: str | None = None


@dataclass
class Source:
    """Source definition."""

    beamline: str
    facility: Facility = Facility(
        "Diamond Light Source",
        "DLS",
        "Synchrotron X-ray Source",
        None,
    )
    probe: str | None = None

    @property
    def set_instrument_name(self) -> str:
        """Set the instrument name from the details saved in source.

        If source type is not defined a priori, the function will assume it is a Synchrotron.
        If the facility_id is defined inside the source dictionary, that is the value that will be used.
        Naming tries to follow the recommended convention for NXmx:
        https://mmcif.wwpdb.org/dictionaries/mmcif_pdbx_v50.dic/Items/_diffrn_source.type.html

        Returns:
            name (str): The name to write under '/entry/instrument/name'
        """
        facility_id = "DIAMOND" if not self.facility.id else self.facility.id

        if not self.facility.type or "SYNCHROTRON" not in self.facility.type.upper():
            return f"{facility_id} {self.beamline}"
        else:
            return f"{facility_id} BEAMLINE {self.beamline}"

    def _generate_source_dict(self):
        source = {
            "name": self.facility.name,
            "type": self.facility.type,
            "short_name": self.facility.short_name,
            "beamline_name": self.beamline,
        }
        if self.probe:
            source["probe"] = self.probe
        if self.facility.id:
            source["facility_id"] = self.facility.id
        return source

    def to_dict(self):
        """Write source information to a dictionary."""
        return self._generate_source_dict()


@dataclass
class Beam:
    """Beam definition.

    Attributes:
        wavelength (list[float] | float): incident wavelength. For a monochromatic beam this should be a single value, \
            for a polychromatic beam a list of wavelengths.
        wavelength_weights (list[float] | None): For a ploychromatic beam, this is a list of the same length as the \
            wavelength one containing the relative weigths corresponding to each wavelength. Defaults to None.
        flux (float | None): flux incident on beam plane area, if measured. Defaults to None.
    """

    wavelength: list[float] | float
    wavelength_weights: list[float] | None = None
    flux: float | None = None

    def to_dict(self) -> dict:
        return self.__dict__


@dataclass
class Attenuator:
    """Attenuator definition."""

    transmission: float | None

    def to_dict(self) -> dict:
        return self.__dict__
