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
from nexgen.nxs_write.NXmxWriter import NXmxFileWriter


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
