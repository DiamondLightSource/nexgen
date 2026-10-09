from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from nexgen.beamlines.i19_2.parameters import CollectionParams
from nexgen.beamlines.i19_2.serial import (
    serial_nexus_writer,
    serial_nexus_writer_with_strided_vds,
)


@patch("nexgen.beamlines.i19_2.serial.standard_nexus_writer")
def test_serial_nexus_writer(
    mock_writer: MagicMock, dummy_tristan_collection_params: CollectionParams
):
    params = dummy_tristan_collection_params.model_dump()
    serial_nexus_writer(params, "/path/to/somefile.nxs")

    mock_writer.assert_called_once_with(
        params, None, "/path/to/somefile.nxs", None, None
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
