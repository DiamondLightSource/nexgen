import tempfile
from unittest.mock import MagicMock

import h5py
import numpy as np
import pytest

from nexgen.nxs_utils import (
    Attenuator,
    Axis,
    Beam,
    Detector,
    EigerDetector,
    Goniometer,
    Source,
    TransformationType,
)
from nexgen.nxs_write.nxmx_writer import NXmxFileWriter

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


@pytest.fixture
def mock_goniometer() -> Goniometer:
    return Goniometer(
        [
            Axis(
                "omega",
                ".",
                TransformationType.ROTATION,
                (-1, 0, 0),
                start_pos=0,
                increment=1,
                num_steps=90,
            ),
            Axis("sam_z", "omega", TransformationType.TRANSLATION, (0, -1, 0)),
            Axis("sam_y", "sam_z", TransformationType.TRANSLATION, (-1, 0, 0)),
        ],
        {"omega": np.arange(0, 90, 1)},
    )


@pytest.fixture
def mock_source() -> Source:
    return Source("I03")


@pytest.fixture
def mock_beam() -> Beam:
    return Beam(wavelength=0.6)


@pytest.fixture
def mock_polychromatic_beam() -> Beam:
    return Beam(wavelength=[0.6, 0.7], wavelength_weights=[1, 1], flux=30.0)


@pytest.fixture
def mock_attenuator() -> Attenuator:
    return Attenuator(transmission=10.0)


@pytest.fixture
def mock_eiger() -> Detector:
    eiger_params = EigerDetector(
        "Eiger 2X 9M",
        [3262, 3108],
        "CdTe",
        50649,
        -1,
    )
    det_axes = [
        Axis("det_z", ".", TransformationType.TRANSLATION, (0, 0, 1), start_pos=500),
    ]
    return Detector(
        eiger_params,
        det_axes,
        [1590.7, 1643.7],
        0.01,
        [(1, 0, 0), (0, 1, 0)],
    )


@pytest.fixture
def dummy_eiger_meta_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_meta_file = h5py.File(test_hdf_file, "w")
    test_meta_file["config"] = dummy_config
    test_meta_file["_dectris/nimages"] = np.array([90])
    test_meta_file["_dectris/ntrigger"] = np.array([1])
    test_meta_file["_dectris/wavelength"] = np.array([0.6])
    test_meta_file["_dectris/x_pixels_in_detector"] = np.array([3180])
    test_meta_file["_dectris/y_pixels_in_detector"] = np.array([3262])
    test_meta_file["_dectris/detector_distance"] = np.array([0.19])
    test_meta_file["_dectris/bit_depth_readout"] = np.array([32])
    test_meta_file["flatfield"] = np.array([[0, 0, 0]])
    test_meta_file["_dectris/software_version"] = np.bytes_("0.0.0")
    test_meta_file["mask"] = np.array([[0, 1, 1], [1, 0, 0]])
    test_meta_file["_dectris/pixel_mask_applied"] = False
    yield test_meta_file


@pytest.fixture
def dummy_nexus_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    yield test_nexus_file


@pytest.fixture
def dummy_NXmxWriter():
    with tempfile.NamedTemporaryFile(suffix=".nxs", delete=True) as test_nxs_file:
        test_fw = NXmxFileWriter(
            test_nxs_file.name,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            10,
        )
        yield test_fw
