import numpy as np
import pytest

from nexgen.command_line.cli_utils import (
    calculate_scan_range,
    find_grid_scan_axes,
    find_osc_axis,
    reframe_arrays,
    split_arrays,
)

test_goniometer = {
    "axes": ["chi", "sam_z", "sam_y", "sam_x"],
    "depends": [".", "chi", "sam_z", "sam_y"],
    "vectors": [-1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0],
    "types": ["rotation", "translation", "translation", "translation"],
    "units": ["deg", "mm", "mm", "mm"],
    "offsets": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "starts": [0.0, 0.0, 0.0, 0.0],
    "ends": [0.0, 0.0, 2.0, 2.0],
    "increments": [0.0, 0.0, 0.2, 0.2],
}

test_goniometer_small = {
    "axes": ["alpha", "sam_z"],
    "vectors": [1, 0, 0, 0, 0, 1],
    "offsets": [(0, 0, 0), (0, 0, 0)],
}

test_detector = {"axes": ["det_z"], "vectors": [0, 0, 1]}
test_module = {
    "fast_axis": [1, 0, 0],
    "slow_axis": [0, 1, 0],
}

test_new_coords = {
    "convention": "rotate",
    "origin": (0, 0, 0),
    "x": (".", "", "", [1, 0, 0]),
    "y": (".", "", "", [0, -1, 0]),
    "z": (".", "", "", [0, 0, -1]),
}


def test_find_osc_axis():
    # Check that it works for just one angle
    assert find_osc_axis(["phi"], [0.0], [0.0], ["rotation"]) == "phi"

    # Check that it returns the default value (omega) if no rotation axis is found
    assert (
        find_osc_axis(
            test_goniometer["axes"][1:],
            test_goniometer["starts"][1:],
            test_goniometer["ends"][1:],
            test_goniometer["types"][1:],
        )
        == "omega"
    )

    # Check that it finds axis correctly
    assert (
        find_osc_axis(
            test_goniometer["axes"],
            test_goniometer["starts"],
            test_goniometer["ends"],
            test_goniometer["types"],
        )
        == "chi"
    )


def test_find_scan_axes():
    # Check that if there are no moving translation axes it returns an empty list
    assert (
        find_grid_scan_axes(
            test_goniometer["axes"][:2],
            test_goniometer["starts"][:2],
            test_goniometer["ends"][:2],
            test_goniometer["types"][:2],
        )
        == []
    )

    # Just one scan axis (linear scan)
    assert find_grid_scan_axes(
        test_goniometer["axes"][:3],
        test_goniometer["starts"][:3],
        test_goniometer["ends"][:3],
        test_goniometer["types"][:3],
    ) == ["sam_y"]

    # Grid scan
    assert find_grid_scan_axes(
        test_goniometer["axes"],
        test_goniometer["starts"],
        test_goniometer["ends"],
        test_goniometer["types"],
    ) == ["sam_y", "sam_x"]


def test_calc_rotation_range():
    # Check that it writes an array of repeated values when starts == ends
    ax = test_goniometer["axes"][0]
    arr = calculate_scan_range(
        [ax],
        [test_goniometer["starts"][0]],
        [test_goniometer["ends"][0]],
        n_images=10,
        rotation=True,
    )
    assert np.all(arr[ax] == 0.0)
    del arr

    arr = calculate_scan_range([ax], [180.0], [180.0], n_images=10, rotation=True)
    assert np.all(arr[ax] == 180.0)
    assert len(arr[ax]) == 10

    # Check that it calculates the correct range for axis_start
    # Given increments
    assert np.all(
        calculate_scan_range([ax], [0.0], [2.0], axes_increments=[0.5], rotation=True)[
            ax
        ]
        == np.array([0.0, 0.5, 1.0, 1.5])
    )
    # Given number of images
    assert np.all(
        calculate_scan_range([ax], [0.0], [1.0], n_images=2, rotation=True)[ax]
        == np.array([0.0, 0.5])
    )

    # Check reverse rotation calculation
    rev = calculate_scan_range(
        [ax], [0.0], [-1.0], axes_increments=[0.2], rotation=True
    )
    assert rev[ax][0] == 0.0
    assert round(rev[ax][-1], 1) == -0.8


def test_calc_scan_range():
    # Check linear scan
    # From increments
    lin = calculate_scan_range(
        test_goniometer["axes"][-1:],
        test_goniometer["starts"][-1:],
        test_goniometer["ends"][-1:],
        test_goniometer["increments"][-1:],
    )
    assert len(lin) == 1
    assert "sam_x" in lin.keys()
    assert len(lin["sam_x"]) == 11
    assert round(lin["sam_x"][1] - lin["sam_x"][0], 1) == 0.2

    del lin

    # From number of images
    lin = calculate_scan_range(
        test_goniometer["axes"][-1:],
        test_goniometer["starts"][-1:],
        test_goniometer["ends"][-1:],
        n_images=10,
    )
    assert len(lin) == 1
    assert "sam_x" in lin.keys()
    assert len(lin["sam_x"]) == 10
    # assert round(lin["sam_x"][1] - lin["sam_x"][0]) == 0.2

    # Check grid scan
    # From number of images
    grid = calculate_scan_range(
        test_goniometer["axes"][2:],
        test_goniometer["starts"][2:],
        test_goniometer["ends"][2:],
        n_images=(10, 10),
    )
    assert len(grid) == 2
    assert "sam_x" in grid.keys() and "sam_y" in grid.keys()
    assert len(grid["sam_x"]) == len(grid["sam_y"])
    assert len(grid["sam_x"]) == 100
    assert round(grid["sam_x"][1] - grid["sam_x"][0], 1) == 0.2
    assert round(grid["sam_y"][10] - grid["sam_y"][0], 1) == 0.2


def test_reframe_arrays_without_coordinate_conversion():
    reframe_arrays(
        test_goniometer_small,
        test_detector,
        test_module,
    )
    assert test_goniometer_small["vectors"] == [(1, 0, 0), (0, 0, 1)]
    assert test_detector["vectors"] == [(0, 0, 1)]


def test_reframe_arrays_from_imgcif():
    reframe_arrays(
        test_goniometer_small,
        test_detector,
        test_module,
        "imgcif",
    )
    assert test_goniometer_small["vectors"] == [(-1, 0, 0), (0, 0, -1)]
    assert test_detector["vectors"] == [(0, 0, -1)]
    assert test_module["fast_axis"] == (-1, 0, 0)
    assert test_module["slow_axis"] == (0, 1, 0)


def test_reframe_arrays_from_another_coordinate_system():
    test_goniometer_small["vectors"] = [1, 0, 0, 0, 0, 1]
    test_detector["vectors"] = [0, 0, 1]
    test_module["fast_axis"] = [1, 0, 0]
    test_module["slow_axis"] = [0, 1, 0]
    test_module["offsets"] = [0, 0, 0, 0, 0, 0]
    reframe_arrays(
        test_goniometer_small,
        test_detector,
        test_module,
        "rotate",
        test_new_coords,
    )

    assert test_goniometer_small["vectors"] == [(1, 0, 0), (0, 0, -1)]
    assert test_detector["vectors"] == [(0, 0, -1)]
    assert test_module["fast_axis"] == (1, 0, 0)
    assert test_module["slow_axis"] == (0, -1, 0)
    assert test_module["offsets"] == [(0, 0, 0), (0, 0, 0)]


def test_reframe_arrays_fails_if_coordinate_system_ill_defined():
    with pytest.raises(ValueError):
        reframe_arrays(
            test_goniometer_small, test_detector, test_module, "", test_new_coords
        )


def test_reframe_arrays_fails_if_new_coordinate_system_not_defined():
    with pytest.raises(TypeError):
        reframe_arrays(test_goniometer_small, test_detector, test_module, "new")


def test_split_arrays():
    assert split_arrays(["phi"], [1, 0, 0]) == {"phi": (1, 0, 0)}
    two_axes = split_arrays(["omega", "phi"], [1, 0, 0, 0, 1, 0])
    assert two_axes["omega"] == (1, 0, 0) and two_axes["phi"] == (0, 1, 0)
    assert (
        len(split_arrays(["omega", "phi", "chi"], [(1, 0, 0), (0, 1, 0), (0, 0, 1)]))
        == 3
    )


def test_split_arrays_fails_if_wrong_size_arrays():
    with pytest.raises(ValueError):
        split_arrays(["omega", "phi"], [1, 0, 0, 1])
