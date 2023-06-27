import tempfile

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nexgen.beamlines import PumpProbe
from nexgen.beamlines.SSX_expt import run_extruder, run_fixed_target
from nexgen.nxs_utils import Axis, TransformationType

axes_list = [
    Axis("omega", ".", TransformationType.ROTATION, (0, 0, -1)),
    Axis("sam_z", "omega", TransformationType.TRANSLATION, (0, 0, 1)),
    Axis("sam_y", "sam_z", TransformationType.TRANSLATION, (0, 1, 0)),
    Axis("sam_x", "sam_y", TransformationType.TRANSLATION, (1, 0, 0)),
]

test_pump = PumpProbe()
test_pump.status = True
test_pump.exposure = 0.1

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
    assert type(info) is dict
    assert info["exposure"] == 0.1 and info["delay"] is None


def test_run_extruder_with_non_zero_omega():
    axes_list[0].start_pos = 90.0
    gonio, osc, _ = run_extruder(axes_list, 10, test_pump)
    assert gonio[0].start_pos == 90.0
    assert gonio[0].increment == 0.0
    assert_array_equal(osc["omega"], np.repeat(90.0, 10))


@pytest.fixture
def dummy_chipmap_file():
    lines = [
        "01status    P3011       1\n",
        "02status    P3021       0\n",
        "03status    P3031       0\n",
        "04status    P3041       0\n",
    ]
    test_map_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".map", delete=False, encoding="utf-8"
    )
    with test_map_file as map:
        map.writelines(lines)
    yield test_map_file


def test_run_fixed_target(dummy_chipmap_file):
    transl, info = run_fixed_target(
        axes_list,
        test_chip_dict,
        dummy_chipmap_file.name,
        test_pump,
    )
    assert list(transl.keys()) == ["sam_y", "sam_x"]
    assert len(transl["sam_x"]) == len(transl["sam_y"])
    assert len(transl["sam_y"]) == 400
    assert info["n_exposures"] == 1


def test_run_fixed_target_with_wrong_axis_in_list(dummy_chipmap_file):
    with pytest.raises(ValueError):
        _ = run_fixed_target(
            axes_list,
            test_chip_dict,
            dummy_chipmap_file.name,
            test_pump,
            scan_axes=["phi", "sam_x"],
        )


def test_run_fixed_target_with_missing_scan_axis(dummy_chipmap_file):
    with pytest.raises(IndexError):
        _ = run_fixed_target(
            axes_list,
            test_chip_dict,
            dummy_chipmap_file.name,
            test_pump,
            scan_axes=["sam_z"],
        )


def test_fixed_target_raises_error_if_no_chip_info(dummy_chipmap_file):
    with pytest.raises(ValueError):
        _ = run_fixed_target(
            axes_list,
            {},
            dummy_chipmap_file.name,
            test_pump,
        )


def test_fixed_target_for_multiple_exposures(dummy_chipmap_file):
    test_chip_dict["N_EXPOSURES"] = [0, "2"]
    transl, info = run_fixed_target(
        axes_list,
        test_chip_dict,
        dummy_chipmap_file.name,
        test_pump,
    )
    assert list(transl.keys()) == ["sam_y", "sam_x"]
    assert len(transl["sam_x"]) == len(transl["sam_y"])
    assert len(transl["sam_y"]) == 800
    assert info["n_exposures"] == 2


@pytest.fixture
def dummy_chipmap_file_multi_block():
    lines = [
        "01status    P3011       1\n",
        "02status    P3021       1\n",
        "03status    P3031       1\n",
        "04status    P3041       1\n",
    ]
    test_map_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".map", delete=False, encoding="utf-8"
    )
    with test_map_file as map:
        map.writelines(lines)
    yield test_map_file


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
