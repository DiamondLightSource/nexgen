from pathlib import Path
from unittest.mock import MagicMock, patch

from nexgen.beamlines.i19_2.parameters import CollectionParams
from nexgen.beamlines.i19_2.tristan import (
    _get_master_file_name,
    start_writer,
)


def test_get_master_file_name():
    metafile = Path("/path/to/file_01_meta.h5")

    nxs = _get_master_file_name(metafile)

    assert nxs.name == "file_01.nxs"


@patch("nexgen.beamlines.i19_2.tristan.NxObjectsComposite")
def test_start_writer(
    mock_nx_objects: MagicMock, dummy_tristan_collection_params: CollectionParams
):
    master_file = _get_master_file_name(dummy_tristan_collection_params.metafile)
    with patch("nexgen.beamlines.i19_2.tristan.EventNXmxFileWriter") as mock_writer:
        start_writer(dummy_tristan_collection_params, mock_nx_objects, master_file)

        mock_writer().write.assert_called_once_with(
            image_filename="/path/to/somefile",
            start_time=dummy_tristan_collection_params.timestamps[0],
        )
        mock_writer().update_timestamps.assert_called_once_with(
            dummy_tristan_collection_params.timestamps[1], "end_time"
        )
