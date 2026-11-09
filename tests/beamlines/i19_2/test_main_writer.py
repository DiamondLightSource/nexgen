from pathlib import Path
from unittest.mock import MagicMock, patch

from nexgen.beamlines.i19_2.eiger import EigerSettings
from nexgen.beamlines.i19_2.main_writer import basic_nxmx_writer, main_writer_i19
from nexgen.beamlines.i19_2.parameters import (
    CollectionParams,
    ExtraDetectorParams,
)


@patch("nexgen.beamlines.i19_2.main_writer.eiger_writer")
def test_main_writer_i19_for_eiger(
    mock_writer: MagicMock,
    dummy_eiger_collection_params: CollectionParams,
):
    dummy_det_params = ExtraDetectorParams(
        bit_depth=16, stream_format="cbor", vds_mapping="tiled"
    )
    test_master = Path("somefile_w001.nxs")

    expected_eiger_settings = EigerSettings(
        master_file=test_master,
        use_meta=False,
        bit_depth=16,
        data_entry_key="data",
        stream_format="cbor",
    )

    main_writer_i19(dummy_eiger_collection_params, dummy_det_params, test_master, 10)

    mock_writer.assert_called_once_with(
        dummy_eiger_collection_params, expected_eiger_settings, 0, "tiled", 10, None
    )


@patch("nexgen.beamlines.i19_2.main_writer.tristan_writer")
def test_main_writer_i19_for_tristan(
    mock_writer: MagicMock,
    dummy_tristan_collection_params: CollectionParams,
):
    test_master = Path("somefile.nxs")

    main_writer_i19(
        dummy_tristan_collection_params,
        master_file=test_master,
        notes={"well": "004"},
    )

    mock_writer.assert_called_once_with(
        dummy_tristan_collection_params, test_master, {"well": "004"}
    )


@patch("nexgen.beamlines.i19_2.main_writer.setup_logging")
@patch("nexgen.beamlines.i19_2.main_writer.main_writer_i19")
def test_basic_nxmx_writer(mock_writer: MagicMock, mock_log: MagicMock):
    params = {
        "exposure_time": 0.2,
        "beam_center": (1234, 2681),
        "wavelength": 0.6,
        "metafile": "/tmp/test_meta.h5",
        "detector_name": "tristan",
    }

    basic_nxmx_writer(params)

    mock_log.assert_called_once_with(Path("/tmp"))
    mock_writer.assert_called_once_with(
        CollectionParams(**params), ExtraDetectorParams()
    )
