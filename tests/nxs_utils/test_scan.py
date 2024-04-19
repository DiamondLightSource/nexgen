import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_utils.axes import Axis, TransformationType
from nexgen.nxs_utils.scan_utils import (
    ScanAxisError,
    ScanAxisNotFoundError,
    calculate_scan_points,
    identify_grid_scan_axes,
    identify_osc_axis,
)

test_axis_list = [
    Axis("omega", ".", TransformationType.ROTATION, (0, 0, -1), -90),
    Axis("phi", "omega", TransformationType.ROTATION, (0, 0, -1), 180),
    Axis("sam_y", "phi", TransformationType.TRANSLATION, (0, 1, 0), 0, 0.1, 10),
    Axis("sam_x", "sam_y", TransformationType.TRANSLATION, (1, 0, 0), 0, 0.2, 5),
]


def test_identify_osc_axis():
    osc_axis = identify_osc_axis(
        [
            Axis("chi", ".", TransformationType.ROTATION, (0, 0, -1), -90, 0.1, 100),
            Axis("phi", "chi", TransformationType.ROTATION, (0, 0, -1), 180),
        ]
    )
    assert osc_axis == "chi"


def test_identify_osc_axis_with_just_one_rotation_axis():
    osc_axis = identify_osc_axis(
        [Axis("phi", "omega", TransformationType.ROTATION, (0, 0, -1), 180)]
    )
    assert osc_axis == "phi"


def test_identify_osc_axis_from_default_value():
    osc_axis = identify_osc_axis(test_axis_list, default="omega")
    assert osc_axis == "omega"


def test_identify_grid_scan_axis():
    grid_axes = identify_grid_scan_axes(test_axis_list)
    assert "sam_x" in grid_axes
    assert "sam_y" in grid_axes


def test_identify_grid_scan_axis_returns_empty_list_if_no_scan():
    grid_axes = identify_grid_scan_axes(
        [Axis("sam_z", "phi", TransformationType.TRANSLATION, (0, 0, 1), 0)],
    )
    assert grid_axes == []


def test_osc_axis_search_fails_for_multiple_moving_axes():
    with pytest.raises(ScanAxisNotFoundError):
        identify_osc_axis(
            [
                Axis(
                    "chi", ".", TransformationType.ROTATION, (0, 0, -1), -90, 0.1, 100
                ),
                Axis(
                    "phi", "chi", TransformationType.ROTATION, (0, 0, -1), 180, 0.5, 50
                ),
            ]
        )


def test_osc_axis_search_fails_for_no_axes():
    with pytest.raises(ScanAxisNotFoundError):
        identify_osc_axis([])


def test_grid_axis_search_fails_for_no_axes():
    with pytest.raises(ScanAxisNotFoundError):
        identify_grid_scan_axes([])


def test_calculate_scan_points_for_rotation_scan():
    ax = Axis("chi", ".", TransformationType.ROTATION, (0, 0, -1), 0.0, 0.5, 4)
    rot = calculate_scan_points(ax, rotation=True)
    assert "chi" in rot.keys()
    assert len(rot["chi"]) == 4
    assert rot["chi"][0] == ax.start_pos
    assert rot["chi"][-1] == ax.end_pos
    assert_array_equal(rot["chi"], np.array([0.0, 0.5, 1.0, 1.5]))


def test_calculate_scan_points_for_reverse_rotation():
    ax = Axis("phi", ".", TransformationType.ROTATION, (0, 0, -1), 0.0, -0.2, 5)
    rev = calculate_scan_points(ax, rotation=True)
    assert rev[ax.name][0] == 0.0
    assert round(rev[ax.name][-1], 1) == -0.8


def test_calculate_omega_points_for_no_rotation():
    rot = calculate_scan_points(test_axis_list[0], rotation=True, tot_num_imgs=10)
    assert test_axis_list[0].name in rot.keys()
    assert len(rot[test_axis_list[0].name]) == 10
    assert_array_equal(
        rot[test_axis_list[0].name], np.repeat(test_axis_list[0].start_pos, 10)
    )


def test_calculate_scan_points_fails_for_wrong_axis_type():
    with pytest.raises(ScanAxisError):
        calculate_scan_points(test_axis_list[-1], rotation=True)


def test_calculate_scan_points_fails_for_missing_number_of_steps():
    with pytest.raises(ValueError):
        calculate_scan_points(test_axis_list[0], rotation=True)


def test_calculate_scan_points_for_linear_scan():
    lin = calculate_scan_points(test_axis_list[-1])
    assert len(lin) == 1
    assert "sam_x" in lin.keys()
    assert len(lin["sam_x"]) == test_axis_list[-1].num_steps
    assert round(lin["sam_x"][1] - lin["sam_x"][0], 1) == test_axis_list[-1].increment


def test_calculate_scan_points_for_snaked_grid_scan():
    grid = calculate_scan_points(
        test_axis_list[-2],
        test_axis_list[-1],
    )
    assert "sam_x" in grid.keys() and "sam_y" in grid.keys()
    assert len(grid["sam_x"]) == len(grid["sam_y"])
    assert round(grid["sam_x"][1] - grid["sam_x"][0], 1) == 0.2
    assert grid["sam_x"][-1] == test_axis_list[-1].start_pos


def test_calculate_scan_points_for_non_snaked_grid_scan():
    grid = calculate_scan_points(
        test_axis_list[-2],
        test_axis_list[-1],
        snaked=False,
    )
    assert "sam_x" in grid.keys() and "sam_y" in grid.keys()
    assert (
        len(grid["sam_x"])
        == test_axis_list[-2].num_steps * test_axis_list[-1].num_steps
    )
    assert round(grid["sam_y"][5] - grid["sam_y"][0], 1) == 0.1
    assert grid["sam_x"][-1] == test_axis_list[-1].end_pos
