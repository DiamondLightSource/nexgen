from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from nexgen.beamlines.I19_2_nxs import (
    CollectionParams,
    DetAxisPosition,
    DetectorName,
    GonioAxisPosition,
    eiger_writer,
    serial_nexus_writer,
)


@pytest.fixture
def dummy_eiger_collection_params():
    return CollectionParams(
        exposure_time=0.01,
        beam_center=(100, 200),
        wavelength=0.4,
        metafile="/path/to/somefile_meta.h5",
        detector_name=DetectorName.EIGER,
    )


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


@patch("nexgen.beamlines.I19_2_nxs.log.config")
def test_nexus_writer_fails_if_missing_n_imgs_and_not_using_meta(
    mock_log_config, dummy_eiger_collection_params
):
    dummy_eiger_collection_params.tot_num_images = None
    with pytest.raises(ValueError):
        eiger_writer(
            Path("/path/to/master.nxs"), dummy_eiger_collection_params, use_meta=False
        )


def test_eiger_nxs_writer_fails_if_missing_axes_and_no_meta(
    dummy_eiger_collection_params,
):
    with pytest.raises(ValueError):
        eiger_writer(
            Path("/path/to/meta"), dummy_eiger_collection_params, use_meta=False
        )


@patch("nexgen.beamlines.I19_2_nxs.logger")
@patch("nexgen.beamlines.I19_2_nxs.log.config")
@patch("nexgen.beamlines.I19_2_nxs.eiger_writer")
def test_serial_nexus_writer_calls_correct_writer_for_eiger(
    mock_eiger_writer, mock_log_config, mock_logger, dummy_eiger_collection_params
):
    serial_nexus_writer(
        dummy_eiger_collection_params.model_dump(),
        Path("path/to/somefile.nxs"),
        (None, None),
        use_meta=True,
    )

    mock_log_config.assert_called_once()
    mock_eiger_writer.assert_called_once_with(
        Path("path/to/somefile.nxs"),
        dummy_eiger_collection_params,
        (None, None),
        True,
        None,
        0,
        None,
    )


@patch("nexgen.beamlines.I19_2_nxs.logger")
@patch("nexgen.beamlines.I19_2_nxs.log.config")
@patch("nexgen.beamlines.I19_2_nxs.tristan_writer")
def test_serial_nexus_writer_calls_correct_writer_for_tristan(
    mock_tristan_writer, mock_log_config, mock_logger, dummy_tristan_collection_params
):
    start_time = datetime.strptime("2025-05-19T11:59:02", "%Y-%m-%dT%H:%M:%S")
    serial_nexus_writer(
        dummy_tristan_collection_params.model_dump(),
        Path("path/to/somefile.nxs"),
        (start_time, None),
        use_meta=True,
    )

    assert mock_logger.info.call_count == 4
    mock_tristan_writer.assert_called_once_with(
        Path("path/to/somefile.nxs"),
        dummy_tristan_collection_params,
        ("2025-05-19T11:59:02Z", None),
        None,
    )
