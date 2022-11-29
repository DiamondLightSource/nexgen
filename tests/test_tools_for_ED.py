import tempfile

import h5py
import numpy as np
import pytest

from nexgen.nxs_write.EDNexusWriter import ED_call_writers
from nexgen.tools.ED_tools import (
    SinglaMaster,
    centroid_max,
    extract_from_SINGLA_master,
    find_beam_centre,
)

test_goniometer = {
    "axes": ["alpha", "sam_z"],
    "vectors": [1, 0, 0, 0, 0, 1],
    "offsets": [(0, 0, 0), (0, 0, 0)],
}
test_detector = {"axes": ["det_z"], "vectors": [0, 0, 1]}
test_module = {
    "fast_axis": [1, 0, 0],
    "slow_axis": [0, 1, 0],
    "offsets": [0, 0, 0, 0, 0, 0],
}

test_new_coords = {
    "convention": "rotate",
    "origin": (0, 0, 0),
    "x": (".", "", "", [1, 0, 0]),
    "y": (".", "", "", [0, -1, 0]),
    "z": (".", "", "", [0, 0, -1]),
}

test_flatfield = np.array([[0, 0, 0], [0, 0, 0]])


def test_ED_call_fails_if_missing_required_argument():
    with pytest.raises(TypeError):
        ED_call_writers("", [], test_goniometer, test_detector, test_module)


def test_ED_call_fails_if_empty_dictionary_passed():
    with pytest.raises(KeyError):
        ED_call_writers(
            "", [], test_goniometer, test_detector, {}, {}, {}, test_new_coords
        )


@pytest.fixture
def dummy_singla_master_file():
    test_hdf_file = tempfile.NamedTemporaryFile(suffix=".h5", delete=True)
    with h5py.File(test_hdf_file, "w") as test_master_file:
        test_master_file["/entry/instrument/detector/description/"] = b"Dectris Singla"
        test_master_file["/entry/instrument/detector/pixel_mask_applied"] = False
        test_master_file[
            "/entry/instrument/detector/detectorSpecific/flatfield"
        ] = test_flatfield
        test_master_file[
            "/entry/instrument/detector/detectorSpecific/software_version"
        ] = b"0.0.0"
        test_master_file["/entry/instrument/detector/nimages"] = 100
    yield test_hdf_file


def test_isSingla_master_file(dummy_singla_master_file):
    assert SinglaMaster.isDectrisSingla(dummy_singla_master_file.name)


def test_get_mask_and_flatfield_from_singla_master_file(dummy_singla_master_file):
    D = extract_from_SINGLA_master(dummy_singla_master_file.name)
    assert "pixel_mask" in D.keys() and "flatfield" in D.keys()
    assert D["pixel_mask"] is None
    assert D["pixel_mask_applied"] == 0
    assert np.all(D["flatfield"] == test_flatfield)
    assert D["flatfield_applied"] is None


def test_get_software_version_from_singla_master_file(dummy_singla_master_file):
    D = extract_from_SINGLA_master(dummy_singla_master_file.name)
    assert "software_version" in D.keys()
    assert type(D["software_version"]) is bytes
    assert D["software_version"].decode() == "0.0.0"


def test_get_nimages_and_triggers(dummy_singla_master_file):
    with h5py.File(dummy_singla_master_file.name, "r") as fh:
        master = SinglaMaster(fh)
        nimages = master.get_number_of_images()
        ntriggers = master.get_number_of_triggers()
        mode = master.get_trigger_mode()
    assert nimages is not None
    assert ntriggers is None and mode is None


def test_centroid_max_calculation():
    test_image = np.array([[0, 1, 2], [3, 4, 5]])
    x, y = centroid_max(test_image)
    assert (x, y) == (2.0, 1.0)


def test_find_beam_center_if_no_pixel_mask(dummy_singla_master_file):
    beam_center = find_beam_centre(dummy_singla_master_file.name, "")
    assert beam_center is None
