import tempfile

import h5py
import numpy as np
import pytest

from nexgen.nxs_utils import Axis, TransformationType
from nexgen.tools.meta_reader import (
    define_vds_data_type,
    update_axes_from_meta,
)
from nexgen.tools.metafile import DectrisMetafile, TristanMetafile


@pytest.fixture
def axes_list() -> list[Axis]:
    return [
        Axis("omega", ".", TransformationType.ROTATION, (0, 0, -1)),
        Axis("sam_z", "omega", TransformationType.TRANSLATION, (0, 0, 1)),
        Axis("sam_y", "sam_z", TransformationType.TRANSLATION, (0, 1, 0)),
        Axis("sam_x", "sam_y", TransformationType.TRANSLATION, (1, 0, 0)),
        Axis("phi", "sam_x", TransformationType.ROTATION, (0, 0, 1)),
    ]


test_detector_size = (512, 1028)  # slow, fast
test_beam = {"wavelength": 0.0}

test_detector = {"axes": ["two_theta", "det_z"]}

dummy_config = """{
    "nimages": 10,
    "ntrigger": 1,
    "omega_increment": 0.0,
    "omega_start": 90.0,
    "phi_increment": 0.1,
    "phi_start": 0.0,
    }"""


def test_Tristan_meta_file():
    test_hdf_file = tempfile.NamedTemporaryFile(suffix=".h5", delete=True)
    with h5py.File(test_hdf_file, "w") as test_meta_file:
        test_meta_file["ts_qty_module00"] = np.zeros(2)
        test_meta_file["ts_qty_module01"] = np.zeros(2)
        assert TristanMetafile(test_meta_file).find_number_of_modules() == 2
        assert TristanMetafile(test_meta_file).find_software_version() is None

    assert TristanMetafile.isTristan(test_hdf_file.name)


@pytest.fixture
def dummy_eiger_meta_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_meta_file = h5py.File(test_hdf_file, "w")
    test_meta_file["config"] = dummy_config
    test_meta_file["_dectris/nimages"] = np.array([10])
    test_meta_file["_dectris/ntrigger"] = np.array([1])
    test_meta_file["_dectris/wavelength"] = np.array([0.6])
    test_meta_file["_dectris/x_pixels_in_detector"] = np.array([test_detector_size[1]])
    test_meta_file["_dectris/y_pixels_in_detector"] = np.array([test_detector_size[0]])
    test_meta_file["_dectris/phi_start"] = np.array([0.0])
    test_meta_file["_dectris/phi_increment"] = np.array([0.1])
    test_meta_file["_dectris/omega_start"] = np.array([90.0])
    test_meta_file["_dectris/omega_increment"] = np.array([0.0])
    test_meta_file["_dectris/two_theta_start"] = np.array([0.0])
    test_meta_file["_dectris/two_theta_increment"] = np.array([0.0])
    test_meta_file["_dectris/detector_distance"] = np.array([0.19])
    test_meta_file["_dectris/bit_depth_image"] = np.array([32])
    yield test_meta_file


def test_Eiger_meta_file(dummy_eiger_meta_file):
    meta = DectrisMetafile(dummy_eiger_meta_file)
    assert meta.hasDectrisGroup
    assert meta.hasMask is False and meta.hasFlatfield is False
    assert meta.read_dectris_config() == {
        "nimages": 10,
        "ntrigger": 1,
        "wavelength": 0.6,
        "x_pixels_in_detector": 1028,
        "y_pixels_in_detector": 512,
        "detector_distance": 0.19,
        "omega_increment": 0.0,
        "omega_start": 90.0,
        "phi_increment": 0.1,
        "phi_start": 0.0,
        "two_theta_increment": 0.0,
        "two_theta_start": 0.0,
        "bit_depth_image": 32,
    }
    assert meta.get_number_of_images() == 10
    assert meta.get_number_of_triggers() == 1
    assert meta.get_full_number_of_images() == 10
    assert meta.get_detector_size() == test_detector_size
    assert meta.hasConfig
    assert meta.read_config_dset() == {
        "nimages": 10,
        "ntrigger": 1,
        "omega_increment": 0.0,
        "omega_start": 90.0,
        "phi_increment": 0.1,
        "phi_start": 0.0,
    }


def test_define_vds_shape(dummy_eiger_meta_file):
    meta = DectrisMetafile(dummy_eiger_meta_file)
    vds_shape = define_vds_data_type(meta)
    assert vds_shape is not None
    assert vds_shape == np.uint32


def test_update_axes_from_meta(dummy_eiger_meta_file, axes_list):
    meta = DectrisMetafile(dummy_eiger_meta_file)
    assert axes_list[0].start_pos == 0.0  # omega
    assert axes_list[-1].start_pos == 0.0  # phi
    update_axes_from_meta(meta, axes_list, osc_axis="phi")
    assert axes_list[0].start_pos == 90.0  # omega
    assert axes_list[-1].start_pos == 0.0  # phi
    assert axes_list[-1].num_steps == 10


def test_update_axes_from_meta_using_config(dummy_eiger_meta_file, axes_list):
    meta = DectrisMetafile(dummy_eiger_meta_file)
    # Reset axes
    axes_list[0].start_pos = 0.0
    axes_list[-1].start_pos = 0.0
    update_axes_from_meta(meta, axes_list, osc_axis="phi", use_config=True)
    assert axes_list[0].start_pos == 90.0  # omega
    assert axes_list[-1].start_pos == 0.0  # phi
    assert axes_list[-1].num_steps == 10
