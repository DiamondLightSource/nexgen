import tempfile

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nexgen.beamlines import PumpProbe
from nexgen.beamlines.SSX_expt import run_extruder, run_fixed_target

test_goniometer = {
    "axes": ["omega", "sam_z", "sam_y", "sam_x"],
    "depends": [".", "omega", "sam_z", "sam_y"],
    "types": ["rotation", "translation", "translation", "translation"],
    "starts": [0.0, 0.0, 0.0, 0.0],
    "ends": [0.0, 0.0, 2.0, 2.0],
    "increments": [0.0, 0.0, 0.2, 0.2],
}

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
    gonio, osc, info = run_extruder(test_goniometer, 10, test_pump)
    l = len(gonio["axes"])
    assert gonio["starts"] == l * [0.0]
    assert gonio["ends"] == l * [0.0]
    assert list(osc.keys()) == ["omega"]
    assert_array_equal(osc["omega"], np.zeros(10))
    assert type(info) is dict
    assert info["exposure"] == 0.1 and info["delay"] is None


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
    gonio, osc, transl, info = run_fixed_target(
        test_goniometer,
        test_chip_dict,
        dummy_chipmap_file.name,
        test_pump,
    )
    assert list(osc.keys()) == ["omega"]
    assert list(transl.keys()) == ["sam_y", "sam_x"]
    assert len(transl["sam_x"]) == len(transl["sam_y"])
    assert len(transl["sam_y"]) == 400
    assert gonio["starts"] == [0.0, 0.0, 0.0, 0.0]
    ends = [e + i for e, i in zip(gonio["ends"], gonio["increments"])]
    assert ends == [0.0, 0.0, 2.5, 2.5]
    assert info["n_exposures"] == 1


def test_run_fixed_target_with_wrong_osc_axis(dummy_chipmap_file):
    with pytest.raises(ValueError):
        _ = run_fixed_target(
            test_goniometer,
            test_chip_dict,
            dummy_chipmap_file.name,
            test_pump,
            osc_axis="phi",
        )


def test_run_extruder_with_non_zero_omega():
    test_goniometer["starts"] = [90.0, 0.0, 0.0, 0.0]
    gonio, osc, _ = run_extruder(test_goniometer, 10, test_pump)
    assert gonio["starts"] == gonio["ends"]
    assert gonio["starts"][0] == 90.0
    assert_array_equal(osc["omega"], np.repeat(90.0, 10))


def test_run_extruder_with_no_goniometer_starts_set():
    test_goniometer["starts"] = None
    gonio, osc, _ = run_extruder(test_goniometer, 10, test_pump)
    assert gonio["starts"] == [0.0, 0.0, 0.0, 0.0]
    assert_array_equal(osc["omega"], np.repeat(0.0, 10))


def test_run_fixed_target_with_non_zero_omega(dummy_chipmap_file):
    test_goniometer["starts"] = [180.0, 0.0, 0.0, 0.0]
    test_goniometer["ends"][0] = 180.0
    gonio, osc, _, _ = run_fixed_target(
        test_goniometer,
        test_chip_dict,
        dummy_chipmap_file.name,
        test_pump,
    )
    assert gonio["starts"] == [180.0, 0.0, 0.0, 0.0]
    ends = [e + i for e, i in zip(gonio["ends"], gonio["increments"])]
    assert ends == [180.0, 0.0, 2.5, 2.5]
    assert len(osc["omega"]) == 400
    assert_array_equal(osc["omega"], np.repeat(180.0, 400))


def test_fixed_target_sanity_check_on_rotation_axis_end(dummy_chipmap_file):
    test_goniometer["starts"] = [-60.0, 0.0, 0.0, 0.0]
    test_goniometer["ends"] = [30.0, 0.0, 0.0, 0.0]

    gonio, osc, _, _ = run_fixed_target(
        test_goniometer,
        test_chip_dict,
        dummy_chipmap_file.name,
        test_pump,
    )

    assert gonio["starts"][0] == gonio["ends"][0]
    ends = [e + i for e, i in zip(gonio["ends"], gonio["increments"])]
    assert ends == [-60.0, 0.0, 2.5, 2.5]
    assert_array_equal(osc["omega"], np.repeat(-60.0, 400))


def test_fixed_target_with_no_goniometer_start_or_end_set(dummy_chipmap_file):
    test_goniometer["starts"] = None
    test_goniometer["ends"] = None
    gonio, osc, _, _ = run_fixed_target(
        test_goniometer,
        test_chip_dict,
        dummy_chipmap_file.name,
        test_pump,
    )
    assert gonio["starts"] == [0.0, 0.0, 0.0, 0.0]
    assert gonio["starts"][0] == gonio["ends"][0]
    assert_array_equal(osc["omega"], np.repeat(0.0, 400))


def test_fixed_target_raises_error_if_no_chip_info(dummy_chipmap_file):
    with pytest.raises(ValueError):
        _ = run_fixed_target(
            test_goniometer,
            None,
            dummy_chipmap_file.name,
            test_pump,
        )


def test_fixed_target_for_multiple_exposures(dummy_chipmap_file):
    test_goniometer["starts"] = None
    test_goniometer["ends"] = None
    test_chip_dict["N_EXPOSURES"] = [0, "2"]
    gonio, osc, transl, info = run_fixed_target(
        test_goniometer,
        test_chip_dict,
        dummy_chipmap_file.name,
        test_pump,
    )
    assert list(osc.keys()) == ["omega"]
    assert list(transl.keys()) == ["sam_y", "sam_x"]
    assert len(transl["sam_x"]) == len(transl["sam_y"])
    assert len(transl["sam_y"]) == 800
    assert gonio["starts"] == [0.0, 0.0, 0.0, 0.0]
    ends = [e + i for e, i in zip(gonio["ends"], gonio["increments"])]
    assert ends == [0.0, 0.0, 2.5, 2.5]
    assert info["n_exposures"] == 2
    assert_array_equal(osc["omega"], np.repeat(0.0, 800))
