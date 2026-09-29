import tempfile

import h5py
import numpy as np
import pytest

from nexgen.beamlines.i19_2.constants import I19_2_EIGER
from nexgen.beamlines.i19_2.eiger import EigerSettings
from nexgen.beamlines.i19_2.parameters import (
    CollectionParams,
    DetAxisPosition,
    DetectorName,
    GonioAxisPosition,
)
from nexgen.nxs_utils.axes import Axis


@pytest.fixture
def eiger_gonio_axes() -> list[Axis]:
    return I19_2_EIGER.gonio


@pytest.fixture
def eiger_det_axes() -> list[Axis]:
    return I19_2_EIGER.det_axes


@pytest.fixture
def dummy_eiger_collection_params() -> CollectionParams:
    return CollectionParams(
        exposure_time=0.01,
        beam_center=(100, 200),
        wavelength=0.4,
        metafile="/path/to/somefile_meta.h5",
        detector_name=DetectorName.EIGER,
    )


@pytest.fixture
def dummy_eiger_settings_cbor() -> EigerSettings:
    return EigerSettings(master_file="/path/to/somefile.nxs", stream_format="cbor")


@pytest.fixture
def dummy_eiger_legacy_meta_file():
    dummy_config = """{
    "nimages": 90,
    "ntrigger": 1,
    "omega_increment": 1.0,
    "omega_start": 0.0,
    "phi_increment": 0.0,
    "phi_start": 0.0,
    "two_theta_start": 10.,
    "two_theta_increment": 0.0,
    }"""
    # test_hdf_file = tempfile.TemporaryFile()
    test_hdf_file = tempfile.NamedTemporaryFile(suffix=".h5", delete=True)
    with h5py.File(test_hdf_file, "w") as test_meta_file:
        test_meta_file["config"] = dummy_config
        test_meta_file["_dectris/nimages"] = np.array([90])
        test_meta_file["_dectris/ntrigger"] = np.array([1])
        test_meta_file["_dectris/wavelength"] = np.array([0.6])
        test_meta_file["_dectris/x_pixels_in_detector"] = np.array([3180])
        test_meta_file["_dectris/y_pixels_in_detector"] = np.array([3262])
        test_meta_file["_dectris/detector_distance"] = np.array([0.19])
        test_meta_file["_dectris/bit_depth_readout"] = np.array([32])
        test_meta_file["_dectris/bit_depth_image"] = np.array([32])
        test_meta_file["flatfield"] = np.array([[0, 0, 0]])
        test_meta_file["_dectris/software_version"] = np.bytes_("0.0.0")
        test_meta_file["mask"] = np.array([[0, 1, 1], [1, 0, 0]])
        test_meta_file["_dectris/pixel_mask_applied"] = np.array([0])  # False
    # yield test_meta_file
    yield test_hdf_file


@pytest.fixture
def dummy_tristan_collection_params():
    return CollectionParams(
        exposure_time=300,
        beam_center=(100, 200),
        wavelength=0.4,
        metafile="/path/to/somefile_meta.h5",
        detector_name=DetectorName.TRISTAN,
        axes_pos=[
            GonioAxisPosition(id="omega", start=-90, end=-20),
            GonioAxisPosition(id="phi", start=0.0),
        ],
        det_pos=[DetAxisPosition(id="det_z", start=250.0)],
    )
