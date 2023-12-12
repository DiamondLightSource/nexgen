import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nexgen.beamlines.beamline_utils import PumpProbe
from nexgen.beamlines.SSX_expt import run_extruder, run_fixed_target
from tests.beamlines.conftest import axes_list

test_pump = PumpProbe()
test_pump.pump_status = True
test_pump.pump_exposure = 0.1

test_chip_dict = {
    "X_NUM_STEPS": [0, 20],
    "Y_NUM_STEPS": [0, 20],
    "X_STEP_SIZE": [0, 0.125],
    "Y_STEP_SIZE": [0, 0.125],
    "X_START": [0, 0],
    "Y_START": [0, 0],
    "Z_START": [0, 0],
    "X_NUM_BLOCKS": [0, 2],
    "Y_NUM_BLOCKS": [0, 2],
    "X_BLOCK_SIZE": [0, 3.175],
    "Y_BLOCK_SIZE": [0, 3.175],
    "N_EXPOSURES": [0, 1],
    "PUMP_REPEAT": [0, 0],
}


def test_run_extruder():
    gonio, osc, info = run_extruder(axes_list, 10, test_pump, "omega")
    idx = [n for n, ax in enumerate(axes_list) if ax.name == "omega"][0]
    assert gonio[idx].start_pos == 0.0
    assert gonio[idx].increment == 0.0
    assert gonio[idx].num_steps == 10
    assert list(osc.keys()) == ["omega"]
    assert_array_equal(osc["omega"], np.zeros(10))
    assert isinstance(info, dict)
    assert info["pump_exposure"] == 0.1 and info["pump_delay"] is None


def test_run_extruder_with_non_zero_omega():
    axes_list[0].start_pos = 90.0
    gonio, osc, _ = run_extruder(axes_list, 10, test_pump)
    assert gonio[0].start_pos == 90.0
    assert gonio[0].increment == 0.0
    assert_array_equal(osc["omega"], np.repeat(90.0, 10))


def test_run_fixed_target(dummy_chipmap_file_single_block):
    transl, info = run_fixed_target(
        axes_list,
        test_chip_dict,
        dummy_chipmap_file_single_block.name,
        test_pump,
    )
    assert list(transl.keys()) == ["sam_y", "sam_x"]
    assert len(transl["sam_x"]) == len(transl["sam_y"])
    assert len(transl["sam_y"]) == 400
    assert info["n_exposures"] == 1


def test_run_fixed_target_with_wrong_axis_in_list(dummy_chipmap_file_single_block):
    with pytest.raises(ValueError):
        _ = run_fixed_target(
            axes_list,
            test_chip_dict,
            dummy_chipmap_file_single_block.name,
            test_pump,
            scan_axes=["phi", "sam_x"],
        )


def test_run_fixed_target_with_missing_scan_axis(dummy_chipmap_file_single_block):
    with pytest.raises(IndexError):
        _ = run_fixed_target(
            axes_list,
            test_chip_dict,
            dummy_chipmap_file_single_block.name,
            test_pump,
            scan_axes=["sam_z"],
        )


def test_fixed_target_raises_error_if_no_chip_info(dummy_chipmap_file_single_block):
    with pytest.raises(ValueError):
        _ = run_fixed_target(
            axes_list,
            {},
            dummy_chipmap_file_single_block.name,
            test_pump,
        )


def test_fixed_target_for_multiple_exposures(dummy_chipmap_file_single_block):
    test_chip_dict["N_EXPOSURES"] = [0, "2"]
    transl, info = run_fixed_target(
        axes_list,
        test_chip_dict,
        dummy_chipmap_file_single_block.name,
        test_pump,
    )
    assert list(transl.keys()) == ["sam_y", "sam_x"]
    assert len(transl["sam_x"]) == len(transl["sam_y"])
    assert len(transl["sam_y"]) == 800
    assert info["n_exposures"] == 2


def test_fixed_target_with_upwards_blocks(dummy_chipmap_file_multi_block):
    test_chip_dict["N_EXPOSURES"] = [0, "1"]
    transl, info = run_fixed_target(
        axes_list,
        test_chip_dict,
        dummy_chipmap_file_multi_block.name,
        test_pump,
    )
    assert list(transl.keys()) == ["sam_y", "sam_x"]
    assert len(transl["sam_x"]) == len(transl["sam_y"])
    assert len(transl["sam_y"]) == 1600
    assert info["n_exposures"] == 1


def test_fixed_target_fullchip_with_multiple_exposures(dummy_chipmap_file_multi_block):
    test_chip_dict["N_EXPOSURES"] = [0, "2"]
    transl, info = run_fixed_target(
        axes_list,
        test_chip_dict,
        dummy_chipmap_file_multi_block.name,
        test_pump,
    )
    assert list(transl.keys()) == ["sam_y", "sam_x"]
    assert len(transl["sam_x"]) == len(transl["sam_y"])
    assert len(transl["sam_y"]) == 3200
    assert info["n_exposures"] == 2
