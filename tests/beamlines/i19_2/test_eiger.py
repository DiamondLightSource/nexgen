from pathlib import Path

import numpy as np
import pytest

from nexgen.beamlines.i19_2.eiger import (
    EigerSettings,
    _check_meta_parameters,
    _define_scan_axis_and_oscillation,
    _get_info_from_legacy_metafile,
)


def test_check_meta_parameters_fails_if_no_meta_and_no_positions_passed(
    dummy_eiger_collection_params,
):
    assert not dummy_eiger_collection_params.axes_pos
    assert not dummy_eiger_collection_params.det_pos
    with pytest.raises(ValueError):
        _check_meta_parameters(dummy_eiger_collection_params, False, None)


def test_check_meta_parameters_fails_if_no_tot_num_images_and_no_frames_passed(
    dummy_eiger_collection_params,
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
    dummy_eiger_collection_params,
    eiger_gonio_axes,
    eiger_det_axes,
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
    dummy_eiger_collection_params, eiger_gonio_axes
):
    assert eiger_gonio_axes[0].increment == 1.0
    dummy_eiger_collection_params.scan_axis = "omega"

    scan_axis, oscillation = _define_scan_axis_and_oscillation(
        dummy_eiger_collection_params, eiger_gonio_axes, 90
    )

    assert scan_axis == "omega"
    assert len(oscillation["omega"]) == 90
