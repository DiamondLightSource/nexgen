import numpy as np
import pytest

from nexgen.nxs_write import (
    calculate_origin,
    calculate_scan_range,
    find_grid_scan_axes,
    find_number_of_images,
    find_osc_axis,
    set_dependency,
    set_instrument_name,
    write_compressed_copy,
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

test_module = {"fast_axis": [1, 0, 0], "slow_axis": [0, 1, 0]}


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


def test_set_dependency():
    # Check that the end of the dependency chain always gets set to b"."
    assert set_dependency(".", "/entry/sample/transformations/") == b"."
    assert set_dependency(test_goniometer["depends"][0]) == b"."
    assert set_dependency("whatever") != b"."

    # Check the path
    assert set_dependency(test_goniometer["depends"][-1], "/entry") == b"/entry/sam_y"


def test_calculate_origin():
    # Check that the default return offset value is 1.0
    beam_center = [1000, 2000]
    pixel_size = [5e-05, 5e-05]
    vec1, val1 = calculate_origin(
        beam_center, pixel_size, test_module["fast_axis"], test_module["slow_axis"]
    )
    assert len(vec1) == 3
    assert val1 == 1.0


def test_find_number_of_images_returns_0_if_no_file_passed():
    n_images = find_number_of_images([])
    assert n_images == 0


def test_set_instrument_name():
    test_source_1 = {"type": "Synchrotron X-Ray Source", "beamline_name": "I24"}
    test_source_2 = {"type": "Electron Microscope", "beamline_name": "eBic"}
    assert set_instrument_name(test_source_1) == "DIAMOND BEAMLINE I24"
    assert set_instrument_name(test_source_2) == "DIAMOND eBic"
    assert (
        set_instrument_name(test_source_2, facility_id="MICROSCOPE")
        == "MICROSCOPE eBic"
    )


def tes_set_instrument_assumes_synchrotron_if_unspecified():
    test_source = {"short_name": "DLS", "beamline_name": "I04"}
    assert set_instrument_name(test_source) == "DIAMOND BEAMLINE I04"


def test_write_copy_raises_error_if_both_array_and_file():
    with pytest.raises(ValueError):
        write_compressed_copy("", "", np.array([0.0]), "filename")
