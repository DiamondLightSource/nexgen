import numpy as np

from nexgen.nxs_write import (
    find_osc_axis,
    find_grid_scan_axes,
    calculate_rotation_scan_range,
    calculate_grid_scan_range,
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
    assert (
        find_grid_scan_axes(
            test_goniometer["axes"][:3],
            test_goniometer["starts"][:3],
            test_goniometer["ends"][:3],
            test_goniometer["types"][:3],
        )
        == ["sam_y"]
    )

    # Grid scan
    assert (
        find_grid_scan_axes(
            test_goniometer["axes"],
            test_goniometer["starts"],
            test_goniometer["ends"],
            test_goniometer["types"],
        )
        == ["sam_y", "sam_x"]
    )


def test_calc_rotation_range():
    # Check that it writes an array of repeated values when starts == ends
    arr = calculate_rotation_scan_range(
        test_goniometer["starts"][0],
        test_goniometer["ends"][0],
        test_goniometer["increments"][0],
        10,
    )
    assert np.all(arr == 0.0)
    del arr

    arr = calculate_rotation_scan_range(180.0, 180.0, 0.1, 10)
    assert np.all(arr == 180.0)
    assert len(arr) == 10

    # Check that it calculates the corrct range
    # Given increments
    assert np.all(
        calculate_rotation_scan_range(0.0, 2.0, 0.5) == np.array([0.0, 0.5, 1.0, 1.5])
    )
    # Given number of images
    assert np.all(
        calculate_rotation_scan_range(0.0, 1.0, 0.1, n_images=2) == np.array([0.0, 1.0])
    )


def test_calc_scan_range():
    # Check linear scan
    lin = calculate_grid_scan_range(
        test_goniometer["axes"][-1:],
        test_goniometer["starts"][-1:],
        test_goniometer["ends"][-1:],
        test_goniometer["increments"][-1:],
    )
    assert len(lin) == 1
    assert "sam_x" in lin.keys()
    assert len(lin["sam_x"]) == 10

    # Check grid scan
    grid = calculate_grid_scan_range(
        test_goniometer["axes"][2:],
        test_goniometer["starts"][2:],
        test_goniometer["ends"][2:],
        test_goniometer["increments"][2:],
        (10, 10),
    )
    assert len(grid) == 2
    assert "sam_x" in grid.keys() and "sam_y" in grid.keys()
    assert len(grid["sam_x"]) == len(grid["sam_y"])
    assert len(grid["sam_x"]) == 100


def test_calculate_origin():
    pass
