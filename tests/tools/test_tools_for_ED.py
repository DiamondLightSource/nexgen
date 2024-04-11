import tempfile
from datetime import datetime

import h5py
import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nexgen.tools.data_writer import build_an_eiger
from nexgen.tools.ed_tools import (
    SinglaMaster,
    centroid_max,
    extract_detector_info_from_master,
    extract_exposure_time_from_master,
    extract_start_time_from_master,
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


@pytest.fixture
def dummy_singla_master_file():
    test_hdf_file = tempfile.NamedTemporaryFile(suffix=".h5", delete=True)
    with h5py.File(test_hdf_file, "w") as test_master_file:
        test_master_file["/entry/instrument/detector/count_time"] = 0.1
        test_master_file[
            "/entry/instrument/detector/detectorSpecific/data_collection_date"
        ] = "2023-12-06T10:30:42.039+02:00"
        test_master_file["/entry/instrument/detector/description/"] = b"Dectris Singla"
        test_master_file["/entry/instrument/detector/pixel_mask_applied"] = False
        test_master_file["/entry/instrument/detector/detectorSpecific/flatfield"] = (
            test_flatfield
        )
        test_master_file[
            "/entry/instrument/detector/detectorSpecific/software_version"
        ] = b"0.0.0"
        test_master_file["/entry/instrument/detector/nimages"] = 100
    yield test_hdf_file


def test_isSingla_master_file(dummy_singla_master_file):
    assert SinglaMaster.isDectrisSingla(dummy_singla_master_file.name)


def test_SignalMaster_get_mask_and_flatfiled(dummy_singla_master_file):
    with h5py.File(dummy_singla_master_file.name, "r") as fh:
        master = SinglaMaster(fh)
        mask_info = master.get_mask()
        flatfield_info = master.get_flatfield()

    assert not mask_info[0]  # mask applied is false
    assert mask_info[1] is None
    assert not flatfield_info[0]  # Flatfield applied is false
    assert_array_equal(flatfield_info[1], test_flatfield)


def test_get_mask_and_flatfield_from_singla_master_file(dummy_singla_master_file):
    D = extract_detector_info_from_master(dummy_singla_master_file.name)
    assert "pixel_mask" in D.keys() and "flatfield" in D.keys()
    assert D["pixel_mask"] is None
    assert D["pixel_mask_applied"] == 0
    assert np.all(D["flatfield"] == test_flatfield)
    assert D["flatfield_applied"] is False


def test_get_software_version_from_singla_master_file(dummy_singla_master_file):
    D = extract_detector_info_from_master(dummy_singla_master_file.name)
    assert "software_version" in D.keys()
    assert isinstance(D["software_version"], bytes)
    assert D["software_version"].decode() == "0.0.0"


def test_get_exposure_time_from_singla_master_file(dummy_singla_master_file):
    exp_time = extract_exposure_time_from_master(dummy_singla_master_file.name)
    assert isinstance(exp_time, float)
    assert exp_time == 0.1


def test_get_collection_start_time_from_singla_master_file(dummy_singla_master_file):
    start_time = extract_start_time_from_master(dummy_singla_master_file.name)
    assert isinstance(start_time, datetime)
    assert start_time == datetime.fromisoformat("2023-12-06T10:30:42")


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


def test_find_beam_center(dummy_singla_master_file):
    # Image and gap size of a Singla detector are the same as a Eiger 1M
    # For the purposes of this test, call build_an_eiger
    image_size = (1062, 1028)
    test_mask = build_an_eiger(image_size, "eiger 1M")
    idx0, idx1 = np.where(test_mask != 0)
    for i, j in zip(idx0, idx1):
        test_mask[i][j] = 1
    with h5py.File(dummy_singla_master_file.name, "w") as fh:
        fh["/entry/instrument/detector/detectorSpecific/pixel_mask"] = test_mask
    test_img = np.zeros((2, *image_size), dtype=np.uint16)
    test_img_hdf_file = tempfile.NamedTemporaryFile(suffix=".h5")
    with h5py.File(test_img_hdf_file, "w") as img:
        # singla specs are the same as eiger 1m so use that for simulation
        img["entry/data/data"] = test_img
    beam_center = find_beam_centre(
        dummy_singla_master_file.name, test_img_hdf_file.name
    )
    assert isinstance(beam_center, tuple)
    assert beam_center[0] is not None
    assert beam_center[1] is not None
