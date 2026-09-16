from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from nexgen.beamlines.i19_2.eiger import (
    EigerSettings,
    _check_meta_parameters,
    _define_scan_axis_and_oscillation,
    _get_info_from_legacy_metafile,
    start_writer,
)
from nexgen.beamlines.i19_2.parameters import CollectionParams
from nexgen.nxs_utils.axes import Axis
from nexgen.tools.vds_tools.utils import VdsSettings


def test_check_meta_parameters_fails_if_no_meta_and_no_positions_passed(
    dummy_eiger_collection_params: CollectionParams,
):
    assert not dummy_eiger_collection_params.axes_pos
    assert not dummy_eiger_collection_params.det_pos
    with pytest.raises(ValueError):
        _check_meta_parameters(dummy_eiger_collection_params, False, None)


def test_check_meta_parameters_fails_if_no_tot_num_images_and_no_frames_passed(
    dummy_eiger_collection_params: CollectionParams,
):
    assert not dummy_eiger_collection_params.tot_num_images
    with pytest.raises(ValueError):
        _check_meta_parameters(dummy_eiger_collection_params, False, None)


def test_eiger_settings_model_default_values():
    eiger_settings = EigerSettings(master_file="/tmp/file_00.nxs")

    assert isinstance(eiger_settings.master_file, Path)
    assert eiger_settings.bit_depth == 32
    assert not eiger_settings.use_meta
    assert eiger_settings.data_entry_key == "data"
    assert eiger_settings.stream_format.value == "legacy"


def test_get_info_from_legacy_meta_file(
    dummy_eiger_legacy_meta_file,
    dummy_eiger_collection_params: CollectionParams,
    eiger_gonio_axes: list[Axis],
    eiger_det_axes: list[Axis],
):
    expected_vds_type = np.uint32
    expected_n_frames = 90

    dummy_eiger_collection_params.metafile = dummy_eiger_legacy_meta_file.name

    vds_dtype, n_frames = _get_info_from_legacy_metafile(
        dummy_eiger_collection_params, eiger_gonio_axes, eiger_det_axes, None
    )

    assert vds_dtype == expected_vds_type
    assert n_frames == expected_n_frames
    assert eiger_gonio_axes[0].increment == 1.0  # omega
    assert eiger_det_axes[1].start_pos == 190.0  # det_z


def test_define_scan_axis_and_oscillation(
    dummy_eiger_collection_params: CollectionParams, eiger_gonio_axes: list[Axis]
):
    assert eiger_gonio_axes[0].increment == 1.0
    dummy_eiger_collection_params.scan_axis = "omega"

    scan_axis, oscillation = _define_scan_axis_and_oscillation(
        dummy_eiger_collection_params, eiger_gonio_axes, 90
    )

    assert scan_axis == "omega"
    assert len(oscillation["omega"]) == 90


@patch("nexgen.beamlines.i19_2.eiger.NxObjectsComposite")
def test_start_writer(
    mock_nx_objects: MagicMock,
    dummy_eiger_collection_params: CollectionParams,
    dummy_eiger_settings_cbor: EigerSettings,
):
    vds_settings = VdsSettings(
        vds_dtype=np.uint32, vds_shape=(45, 2162, 2068), vds_mapping="tiled"
    )
    with patch("nexgen.beamlines.i19_2.eiger.NXmxFileWriter") as mock_writer:
        start_writer(
            dummy_eiger_collection_params,
            dummy_eiger_settings_cbor,
            mock_nx_objects,
            vds_settings,
        )

        mock_writer().write.assert_called_once_with(
            image_filename="/path/to/somefile",
            start_time=dummy_eiger_collection_params.timestamps[0],
            data_entry_key=dummy_eiger_settings_cbor.data_entry_key,
        )
        mock_writer().write_vds.assert_called_once_with(
            vds_offset=0,
            vds_shape=vds_settings.vds_shape,
            vds_dtype=vds_settings.vds_dtype,
            vds_mapping=vds_settings.vds_mapping,
        )
