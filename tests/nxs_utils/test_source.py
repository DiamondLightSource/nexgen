import pytest
from pydantic import ValidationError

from nexgen.nxs_utils.source import Attenuator, Beam, Facility, Source

test_beam = Beam(0.6)
test_polychromatic_beam = Beam(
    wavelength=[0.6, 0.7, 0.9], wavelength_weights=[1, 0.5, 1.2], flux=10
)

test_beamline_source = Source("I03")

test_ed_source = Source(
    "m12",
    Facility("Diamond Light Source", "DLS", "Electron Source", "DIAMOND MICROSCOPE"),
    probe="electrons",
)


def test_beam_default_to_dict():
    beamdict = test_beam.to_dict()
    assert isinstance(beamdict["wavelength"], float)
    assert beamdict["wavelength"] == 0.6
    assert beamdict["flux"] is None


def test_beam_with_added_flux():
    test_beam.flux = 10
    assert test_beam.wavelength == 0.6
    assert test_beam.to_dict()["flux"] == 10


def test_polichromatic_beam_with_flux():
    beam = test_polychromatic_beam.to_dict()
    assert isinstance(beam["wavelength"], list)
    assert beam["wavelength"] == [0.6, 0.7, 0.9]
    assert len(beam["wavelength_weights"]) == len(beam["wavelength"])


def test_attenuator_raises_error_if_nothing_is_passed():
    with pytest.raises(ValidationError):
        Attenuator()


def test_attenuator():
    assert Attenuator(None).transmission is None
    assert Attenuator(10).transmission == 10


def test_source():
    assert test_beamline_source.beamline == "I03"
    assert test_beamline_source.name == "Diamond Light Source"
    assert test_beamline_source.probe is None

    assert test_beamline_source.set_instrument_name() == "DIAMOND BEAMLINE I03"


def test_dource_to_dict():
    sourcedict = test_beamline_source._generate_source_dict()
    assert "beamline_name" in list(sourcedict.keys())
    assert sourcedict["beamline_name"] == test_beamline_source.beamline
    assert "probe" not in list(sourcedict.keys())


def test_source_for_ed():
    assert test_ed_source.beamline == "m12"
    assert test_ed_source.facility_type == "Electron Source"
    assert test_ed_source.probe == "electrons"

    assert test_ed_source.set_instrument_name() == "DIAMOND MICROSCOPE m12"

    assert test_ed_source._generate_source_dict()["facility_id"] == "DIAMOND MICROSCOPE"
