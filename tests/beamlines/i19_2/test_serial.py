from pathlib import Path
from unittest.mock import MagicMock, call, patch

import numpy as np

from nexgen.beamlines.i19_2.parameters import CollectionParams, ExtraDetectorParams
from nexgen.beamlines.i19_2.serial import (
    serial_nexus_writer,
    serial_nexus_writer_with_strided_vds,
)


@patch("nexgen.beamlines.i19_2.serial.setup_logging")
@patch("nexgen.beamlines.i19_2.serial.main_writer_i19")
def test_serial_nexus_writer(
    mock_writer: MagicMock,
    mock_setup_log: MagicMock,
    dummy_tristan_collection_params: CollectionParams,
):
    params = dummy_tristan_collection_params.model_dump()
    serial_nexus_writer(params, "/path/to/somefile.nxs")

    mock_setup_log.assert_called_once_with(
        dummy_tristan_collection_params.metafile.parent
    )
    mock_writer.assert_called_once_with(
        dummy_tristan_collection_params,
        ExtraDetectorParams(),
        Path("/path/to/somefile.nxs"),
        None,
        None,
    )


@patch("nexgen.beamlines.i19_2.serial.setup_logging")
@patch("nexgen.beamlines.i19_2.serial.main_writer_i19")
def test_serial_nexus_writer_in_extg_mode(
    mock_writer: MagicMock,
    mock_setup_log: MagicMock,
    dummy_eiger_collection_params: CollectionParams,
):
    dummy_eiger_collection_params.tot_num_images = 100
    params = dummy_eiger_collection_params.model_dump()
    det_params = {
        "extg_mode": "double",
        "vds_mapping": "strided",
    }
    serial_nexus_writer(
        params, "/path/to/somefile.nxs", det_params, vds_names=["A", "B"]
    )

    mock_setup_log.assert_called_once_with(
        dummy_eiger_collection_params.metafile.parent
    )
    assert mock_writer.call_count == 2
    mock_writer.assert_has_calls(
        [
            call(
                dummy_eiger_collection_params,
                ExtraDetectorParams(
                    extg_mode="double",
                    stream_format="cbor",
                    vds_mapping="strided",
                    vds_offset=0,
                ),
                Path("/path/to/somefile_A.nxs"),
                50,
                None,
            ),
            call(
                dummy_eiger_collection_params,
                ExtraDetectorParams(
                    extg_mode="double",
                    stream_format="cbor",
                    vds_mapping="strided",
                    vds_offset=1,
                ),
                Path("/path/to/somefile_B.nxs"),
                50,
                None,
            ),
        ],
        any_order=True,
    )


@patch("nexgen.beamlines.i19_2.serial.write_strided_vds")
@patch("nexgen.beamlines.i19_2.serial._get_metadata_from_og_nexus")
def test_serial_nexus_writer_with_strided_vds(
    mock_get_metadata: MagicMock, mock_write_vds: MagicMock
):
    test_path = Path("/path/to/somefile.nxs")
    expected_new_path = Path("/path/to/somefile_ES.nxs")
    mock_get_metadata.return_value = [(10, 200, 200), np.uint32]
    with patch("nexgen.beamlines.i19_2.serial.h5py.File") as mock_fh:
        serial_nexus_writer_with_strided_vds(test_path, ["ES"])

        mock_fh.assert_called_once_with(expected_new_path, "r+")
        mock_get_metadata.assert_called_once_with(test_path, expected_new_path)
        mock_write_vds.assert_called_once_with(
            mock_fh().__enter__(), (10, 200, 200), 0, 1, np.uint32
        )
