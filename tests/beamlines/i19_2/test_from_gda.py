from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexgen.beamlines.i19_2.eiger import EigerSettings
from nexgen.beamlines.i19_2.from_gda import _get_params_from_ecr, gda_nexus_writer
from nexgen.beamlines.i19_2.parameters import CollectionParams, ParamsFromGDA


@pytest.fixture
def gda_tristan_params() -> ParamsFromGDA:
    return ParamsFromGDA(
        metafile="/tmp/somefile_meta.h5",
        xmlfile="/tmp/table.xml",
        detector_name="tristan",
        exposure_time=300,
        wavelength=0.4,
        beam_center=(100, 200),
    )


@pytest.fixture
def gda_eiger_params() -> ParamsFromGDA:
    return ParamsFromGDA(
        metafile="/tmp/somefile_meta.h5",
        xmlfile="/tmp/table.xml",
        detector_name="eiger",
        exposure_time=0.01,
        wavelength=0.4,
        beam_center=(100, 200),
        detector_params={"bit_depth": 16},
    )


@patch("nexgen.beamlines.i19_2.from_gda.setup_logging")
@patch("nexgen.beamlines.i19_2.from_gda._get_params_from_ecr")
@patch("nexgen.beamlines.i19_2.from_gda.tristan_writer")
def test_gda_writer_for_tristan(
    mock_writer: MagicMock,
    mock_ecr: MagicMock,
    mock_setup_log: MagicMock,
    gda_tristan_params: ParamsFromGDA,
    dummy_tristan_collection_params: CollectionParams,
):
    mock_ecr.return_value = dummy_tristan_collection_params

    gda_nexus_writer(gda_tristan_params)

    mock_setup_log.assert_called_once_with(Path("/tmp"), "gda_nxs_tristan_writer.log")
    mock_writer.assert_called_once_with(
        dummy_tristan_collection_params, Path("/tmp/somefile.nxs")
    )


@patch("nexgen.beamlines.i19_2.from_gda.setup_logging")
@patch("nexgen.beamlines.i19_2.from_gda._get_params_from_ecr")
@patch("nexgen.beamlines.i19_2.from_gda.eiger_writer")
def test_gda_writer_for_eiger(
    mock_writer: MagicMock,
    mock_ecr: MagicMock,
    mock_setup_log: MagicMock,
    gda_eiger_params: ParamsFromGDA,
    dummy_eiger_collection_params: CollectionParams,
):
    mock_ecr.return_value = dummy_eiger_collection_params
    expected_eiger_settings = EigerSettings(
        master_file=Path("/tmp/somefile.nxs"),
        bit_depth=16,
        use_meta=False,
        data_entry_key="data",
        stream_format="legacy",
    )

    gda_nexus_writer(gda_eiger_params)

    mock_setup_log.assert_called_once_with(Path("/tmp"), "gda_nxs_eiger_writer.log")
    mock_writer.assert_called_once_with(
        dummy_eiger_collection_params, expected_eiger_settings, 0, "blocked"
    )


def test_get_params_from_ecr(dummy_xml_file):
    params = ParamsFromGDA(
        metafile="/tmp/somefile_meta.h5",
        xmlfile=dummy_xml_file.name,
        exposure_time=0.2,
        beam_center=(100, 200),
        detector_name="eiger",
        wavelength=0.6,
    )

    collection_params = _get_params_from_ecr(params)

    assert isinstance(collection_params, CollectionParams)
    assert collection_params.transmission == 10.0
    assert collection_params.tot_num_images == 10
    assert collection_params.det_pos[0].start == 10.0
    assert collection_params.det_pos[1].start == 110.0  # det_z
    assert collection_params.scan_axis == "omega"
