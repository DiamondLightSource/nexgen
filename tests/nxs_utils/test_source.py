import pytest
from pydantic import ValidationError

from nexgen.nxs_utils.source import Attenuator, Beam, Facility, Source


@pytest.fixture
def beam() -> Beam:
    return Beam(0.6)


@pytest.fixture
def polychromatic_beam() -> Beam:
    return Beam(wavelength=[0.6, 0.7, 0.9], wavelength_weights=[1, 0.5, 1.2], flux=10)


@pytest.fixture
def beamline_source() -> Source:
    return Source("I03")


@pytest.fixture
def ed_source() -> Source:
    return Source(
        "m12",
        Facility(
            "Diamond Light Source", "DLS", "Electron Source", "DIAMOND MICROSCOPE"
        ),
        probe="electrons",
    )


def test_beam_default_to_dict(beam):
    beamdict = beam.to_dict()
    assert isinstance(beamdict["wavelength"], float)
    assert beamdict["wavelength"] == 0.6
    assert beamdict["flux"] is None


def test_beam_with_added_flux(beam):
    beam.flux = 10
    assert beam.wavelength == 0.6
    assert beam.to_dict()["flux"] == 10


def test_polichromatic_beam_with_flux(polychromatic_beam):
    beam = polychromatic_beam.to_dict()
    assert isinstance(beam["wavelength"], list)
    assert beam["wavelength"] == [0.6, 0.7, 0.9]
    assert len(beam["wavelength_weights"]) == len(beam["wavelength"])


def test_attenuator_raises_error_if_nothing_is_passed():
    with pytest.raises(ValidationError):
        Attenuator()


def test_attenuator():
    assert Attenuator(None).transmission is None
    assert Attenuator(10).transmission == 10


def test_source(beamline_source):
    assert beamline_source.beamline == "I03"
    assert beamline_source.facility.name == "Diamond Light Source"
    assert beamline_source.probe is None

    assert beamline_source.set_instrument_name == "DIAMOND BEAMLINE I03"


def test_source_to_dict(beamline_source):
    source_dict = beamline_source.to_dict()
    assert "beamline_name" in list(source_dict.keys())
    assert source_dict["beamline_name"] == beamline_source.beamline
    assert "probe" not in list(source_dict.keys())


def test_source_for_ed(ed_source):
    assert ed_source.beamline == "m12"
    assert ed_source.facility.type == "Electron Source"
    assert ed_source.probe == "electrons"

    assert ed_source.set_instrument_name == "DIAMOND MICROSCOPE m12"

    assert ed_source.to_dict()["facility_id"] == "DIAMOND MICROSCOPE"
