import tempfile

import h5py
import numpy as np
import pytest

from nexgen.nxs_write.EDNexusWriter import reframe_arrays
from nexgen.tools.ED_tools import SinglaMaster, extract_from_SINGLA_master

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


def test_reframe_arrays_without_coordinate_conversion():
    reframe_arrays(
        "mcstas",
        test_goniometer,
        test_detector,
        test_module,
        test_new_coords,
    )
    assert test_goniometer["vectors"] == [(1, 0, 0), (0, 0, 1)]
    assert test_module["offsets"] == [(0, 0, 0), (0, 0, 0)]
    assert test_detector["vectors"] == [(0, 0, 1)]


def test_reframe_arrays_from_another_coordinate_system():
    reframe_arrays(
        "rotate",
        test_goniometer,
        test_detector,
        test_module,
        test_new_coords,
    )
    assert test_detector["vectors"] == [(0, 0, -1)]
    assert test_goniometer["vectors"] == [(1, 0, 0), (0, 0, -1)]
    assert test_module["fast_axis"] == (1, 0, 0)
    assert test_module["slow_axis"] == (0, -1, 0)


def test_reframe_arrays_fails_if_coordinate_system_ill_defined():
    with pytest.raises(ValueError):
        reframe_arrays("", test_goniometer, test_detector, test_module, test_new_coords)


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
    assert D["pixel_mask"] is None and D["pixel_mask_applied"] is False
    assert np.all(D["flatfield"] == test_flatfield) is True
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
