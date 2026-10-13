from pathlib import Path
from unittest.mock import MagicMock, patch

from nexgen.beamlines.i19_2.eiger import EigerSettings
from nexgen.beamlines.i19_2.main_writer import _setup_logging, standard_nexus_writer
from nexgen.beamlines.i19_2.parameters import (
    CollectionParams,
)


@patch("nexgen.beamlines.i19_2.main_writer.log")
def test_setup_logging(mock_log: MagicMock):
    _setup_logging(Path("/tmp/data"))

    mock_log.config.assert_called_once_with("/tmp/data/I19_2_nxs_writer.log")


@patch("nexgen.beamlines.i19_2.main_writer._setup_logging")
@patch("nexgen.beamlines.i19_2.main_writer.eiger_writer")
def test_standard_nexus_writer_for_eiger(
    mock_writer: MagicMock,
    mock_setup_log: MagicMock,
    dummy_eiger_collection_params: CollectionParams,
):
    dummy_det_params = {"bit_depth": 16, "stram_format": "cbor", "vds_mapping": "tiled"}
    test_master = Path("somefile_w001.nxs")

    expected_eiger_settings = EigerSettings(
        master_file=test_master,
        use_meta=False,
        bit_depth=16,
        data_entry_key="data",
        stram_format="cbor",
    )

    standard_nexus_writer(
        dummy_eiger_collection_params.model_dump(), dummy_det_params, test_master, 10
    )

    mock_setup_log.assert_called_once_with(
        dummy_eiger_collection_params.metafile.parent
    )
    mock_writer.assert_called_once_with(
        dummy_eiger_collection_params, expected_eiger_settings, 0, "tiled", 10, None
    )


@patch("nexgen.beamlines.i19_2.main_writer._setup_logging")
@patch("nexgen.beamlines.i19_2.main_writer.tristan_writer")
def test_standard_nexus_writer_for_tristan(
    mock_writer: MagicMock,
    mock_setup_log: MagicMock,
    dummy_tristan_collection_params: CollectionParams,
):
    test_master = Path("somefile.nxs")

    standard_nexus_writer(
        dummy_tristan_collection_params.model_dump(),
        master_file=test_master,
        notes={"well": "004"},
    )

    mock_setup_log.assert_called_once_with(
        dummy_tristan_collection_params.metafile.parent
    )
    mock_writer.assert_called_once_with(
        dummy_tristan_collection_params, test_master, {"well": "004"}
    )
