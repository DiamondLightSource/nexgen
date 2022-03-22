from pathlib import Path
from nexgen.nxs_write.NXclassWriters import write_NXdata, find_scan_axis, write_NXsample
from unittest.mock import MagicMock, patch
import pytest
import tempfile
import h5py
from h5py import AttributeManager
import numpy as np
from numpy.testing import assert_array_equal

test_goniometer_axes = {
    "axes": ["omega", "sam_z", "sam_y"],
    "depends": [".", "omega", "sam_z"],
    "vectors": [
        -1,
        0,
        0,
        0,
        -1,
        0,
        -1,
        0,
        0,
    ],
    "types": [
        "rotation",
        "translation",
        "translation",
    ],
    "units": ["deg", "mm", "mm"],
    "offsets": [0, 0, 0, 0, 0, 0, 0, 0, 0],
    "starts": [0, 0, 0],
    "ends": [0, 0, 0],
    "increments": [1, 0, 0],
}


@pytest.fixture
def dummy_nexus_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    yield test_nexus_file


def test_given_no_data_files_when_write_NXdata_then_assert_error():
    mock_hdf5_file = MagicMock()
    with pytest.raises(AssertionError):
        write_NXdata(mock_hdf5_file, [], {}, "", "", {"sam_z": []})


def test_given_no_data_type_specified_when_write_NXdata_then_exception_raised(
    dummy_nexus_file,
):
    with pytest.raises(SystemExit):
        write_NXdata(
            dummy_nexus_file, [Path("tmp")], test_goniometer_axes, "", "", {"sam_z": []}
        )


def test_given_one_data_file_when_write_NXdata_then_data_entry_in_file(
    dummy_nexus_file,
):
    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        "images",
        "",
        {"sam_z": []},
    )
    assert dummy_nexus_file["/entry/data"].attrs["NX_class"] == b"NXdata"
    assert "data" in dummy_nexus_file["/entry/data"]


def test_given_scan_axis_when_write_NXdata_then_axis_in_data_entry_with_correct_data_and_attributes(
    dummy_nexus_file,
):
    test_axis = "sam_z"
    test_scan_range = [0, 1, 2]
    axis_entry = f"/entry/data/{test_axis}"

    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        "images",
        "",
        {test_axis: test_scan_range},
    )

    assert test_axis in dummy_nexus_file["/entry/data"]
    assert dummy_nexus_file["/entry/data"].attrs["axes"] == b"sam_z"
    assert_array_equal(test_scan_range, dummy_nexus_file[axis_entry][:])
    assert (
        dummy_nexus_file[axis_entry].attrs["depends_on"]
        == b"/entry/sample/transformations/omega"
    )
    assert dummy_nexus_file[axis_entry].attrs["transformation_type"] == b"translation"
    assert dummy_nexus_file[axis_entry].attrs["units"] == b"mm"
    assert_array_equal(dummy_nexus_file[axis_entry].attrs["vector"][:], [0.0, -1.0, 0])


def test_given_multiple_scan_axes_when_write_NXdata_then_axis_in_data_entry_with_correct_data_and_attributes(
    dummy_nexus_file,
):
    test_scan = {"sam_z": [0, 1, 2], "omega": [3, 4, 5]}

    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        "images",
        "",
        test_scan,
    )

    axis_entry = f"/entry/data/sam_z"
    assert "sam_z" in dummy_nexus_file["/entry/data"]
    assert_array_equal(test_scan["sam_z"], dummy_nexus_file[axis_entry][:])
    assert (
        dummy_nexus_file[axis_entry].attrs["depends_on"]
        == b"/entry/sample/transformations/omega"
    )
    assert dummy_nexus_file[axis_entry].attrs["transformation_type"] == b"translation"
    assert dummy_nexus_file[axis_entry].attrs["units"] == b"mm"
    assert_array_equal(dummy_nexus_file[axis_entry].attrs["vector"][:], [0.0, -1.0, 0])

    axis_entry = f"/entry/data/omega"
    assert "omega" in dummy_nexus_file["/entry/data"]
    assert_array_equal(test_scan["omega"], dummy_nexus_file[axis_entry][:])
    assert dummy_nexus_file[axis_entry].attrs["depends_on"] == b"."
    assert dummy_nexus_file[axis_entry].attrs["transformation_type"] == b"rotation"
    assert dummy_nexus_file[axis_entry].attrs["units"] == b"deg"
    assert_array_equal(dummy_nexus_file[axis_entry].attrs["vector"][:], [-1.0, 0.0, 0])


def test_given_scan_axis_when_write_NXsample_then_scan_axis_data_copied_from_data_group_as_well_as_increment_set_and_end(
    dummy_nexus_file,
):
    test_axis = "omega"
    test_scan_range = [0, 1, 2]
    axis_entry = f"/entry/sample/sample_{test_axis}/{test_axis}"

    # Doing this to write the scan axis data into the data group
    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        "images",
        "",
        {test_axis: test_scan_range},
    )

    write_NXsample(
        dummy_nexus_file,
        test_goniometer_axes,
        "",
        "images",
        {test_axis: test_scan_range},
    )

    assert f"sample_{test_axis}" in dummy_nexus_file["/entry/sample"]
    assert_array_equal(test_scan_range, dummy_nexus_file[axis_entry][:])
    assert dummy_nexus_file[axis_entry].attrs["depends_on"] == b"."
    assert dummy_nexus_file[axis_entry].attrs["transformation_type"] == b"rotation"
    assert dummy_nexus_file[axis_entry].attrs["units"] == b"deg"
    assert_array_equal(dummy_nexus_file[axis_entry].attrs["vector"][:], [-1, 0, 0])
    assert_array_equal(dummy_nexus_file[axis_entry + "_increment_set"][:], [1] * 3)
    assert dummy_nexus_file[axis_entry + "_end"][1] == 2


def test_given_no_axes_when_find_scan_axis_called_then_assert_error():
    with pytest.raises(AssertionError):
        find_scan_axis([], [], [], [])


def test_given_one_rotation_axis_when_find_scan_axis_called_then_axis_returned():
    test_names = ["sam_x", "omega"]
    test_starts = [0, 0]
    test_ends = [0, 10]
    test_types = ["translation", "rotation"]
    scan_axis = find_scan_axis(test_names, test_starts, test_ends, test_types)
    assert scan_axis == "omega"


def test_given_no_moving_axes_when_find_scan_axis_called_then_default_axis_returned():
    test_names = ["sam_x", "omega"]
    test_starts = [0, 0]
    test_ends = [0, 0]
    test_types = ["rotation", "rotation"]
    default_axis = "default_axis"
    scan_axis = find_scan_axis(
        test_names, test_starts, test_ends, test_types, default_axis
    )
    assert scan_axis == default_axis


def test_given_one_moving_axes_when_find_scan_axis_called_then_this_axis_returned():
    test_names = ["sam_x", "omega"]
    test_starts = [0, 0]
    test_ends = [0, 10]
    test_types = ["rotation", "rotation"]
    default_axis = "default_axis"
    scan_axis = find_scan_axis(
        test_names, test_starts, test_ends, test_types, default_axis
    )
    assert scan_axis == "omega"


def test_given_two_moving_axes_when_find_scan_axis_called_then_exception():
    test_names = ["sam_x", "omega"]
    test_starts = [0, 0]
    test_ends = [10, 10]
    test_types = ["rotation", "rotation"]
    default_axis = "default_axis"
    with pytest.raises(SystemExit):
        scan_axis = find_scan_axis(
            test_names, test_starts, test_ends, test_types, default_axis
        )
