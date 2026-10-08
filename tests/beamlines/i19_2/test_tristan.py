from unittest.mock import MagicMock, patch

import pytest

from nexgen.beamlines.i19_2.parameters import CollectionParams, DetectorName
from nexgen.beamlines.i19_2.tristan import (
    _check_input_parameters,
    start_writer,
)
from nexgen.utils import get_nexus_filename


@patch("nexgen.beamlines.i19_2.tristan.logger")
def test_check_input_parameters_raises_error_if_no_axes(mock_logger: MagicMock):
    bad_tristan_params = CollectionParams(
        exposure_time=300,
        beam_center=(100, 200),
        wavelength=0.4,
        metafile="/path/to/somefile_meta.h5",
        detector_name=DetectorName.TRISTAN,
        scan_axis="phi",
    )
    with pytest.raises(ValueError):
        _check_input_parameters(bad_tristan_params)
        mock_logger.error.assert_called_once()


@patch("nexgen.beamlines.i19_2.tristan.logger")
def test_if_missing_scan_axis_phi_assumed(
    mock_logger: MagicMock, dummy_tristan_collection_params: CollectionParams
):
    _check_input_parameters(dummy_tristan_collection_params)

    mock_logger.warning.assert_called_once()
    assert dummy_tristan_collection_params.scan_axis == "phi"


@patch("nexgen.beamlines.i19_2.tristan.NxObjectsComposite")
def test_start_writer(
    mock_nx_objects: MagicMock, dummy_tristan_collection_params: CollectionParams
):
    master_file = get_nexus_filename(dummy_tristan_collection_params.metafile)
    with patch("nexgen.beamlines.i19_2.tristan.EventNXmxFileWriter") as mock_writer:
        start_writer(dummy_tristan_collection_params, mock_nx_objects, master_file)

        mock_writer().write.assert_called_once_with(
            image_filename="/path/to/somefile",
            start_time=dummy_tristan_collection_params.timestamps[0],
        )
        mock_writer().update_timestamps.assert_called_once_with(
            dummy_tristan_collection_params.timestamps[1], "end_time"
        )
