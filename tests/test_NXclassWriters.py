import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import h5py
import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_write.NXclassWriters import (
    write_NXdata,
    write_NXdatetime,
    write_NXdetector_module,
    write_NXsample,
)

test_module = {"fast_axis": [1, 0, 0], "slow_axis": [0, 1, 0]}

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
    "ends": [90, 0, 0],
    "increments": [1, 0, 0],
}


@pytest.fixture
def dummy_nexus_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    yield test_nexus_file


def test_given_no_data_files_when_write_NXdata_then_assert_error():
    mock_hdf5_file = MagicMock()
    with pytest.raises(OSError):
        write_NXdata(mock_hdf5_file, [], {}, "", "", [])


def test_given_no_data_type_specified_when_write_NXdata_then_exception_raised(
    dummy_nexus_file,
):
    osc_scan = {"omega": np.arange(0, 90, 1)}
    with pytest.raises(ValueError):
        write_NXdata(
            dummy_nexus_file,
            [Path("tmp")],
            test_goniometer_axes,
            ("", 0),
            "",
            osc_scan,
        )


def test_given_one_data_file_when_write_NXdata_then_data_in_file(
    dummy_nexus_file,
):
    osc_scan = {"omega": np.arange(0, 90, 1)}
    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        ("images", 0),
        "",
        osc_scan,
    )
    assert dummy_nexus_file["/entry/data"].attrs["NX_class"] == b"NXdata"
    assert "data_000001" in dummy_nexus_file["/entry/data"]


def test_given_scan_axis_when_write_NXdata_then_axis_in_data_entry_with_correct_data_and_attributes(
    dummy_nexus_file,
):
    test_axis = "omega"
    test_scan_range = np.arange(0, 90, 1)
    axis_entry = f"/entry/data/{test_axis}"
    osc_scan = {test_axis: test_scan_range}

    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        ("images", 0),
        "",
        osc_scan,
    )

    assert test_axis in dummy_nexus_file["/entry/data"]
    assert_array_equal(test_scan_range, dummy_nexus_file[axis_entry][:])
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
    osc_scan = {test_axis: test_scan_range}

    # Doing this to write the scan axis data into the data group
    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        ("images", 0),
        "",
        osc_scan,
    )

    write_NXsample(
        dummy_nexus_file,
        test_goniometer_axes,
        "",
        ("images", 0),
        osc_scan,
    )

    assert f"sample_{test_axis}" in dummy_nexus_file["/entry/sample"]
    assert_array_equal(test_scan_range, dummy_nexus_file[axis_entry][:])
    assert dummy_nexus_file[axis_entry].attrs["depends_on"] == b"."
    assert dummy_nexus_file[axis_entry].attrs["transformation_type"] == b"rotation"
    assert dummy_nexus_file[axis_entry].attrs["units"] == b"deg"
    assert_array_equal(dummy_nexus_file[axis_entry].attrs["vector"][:], [-1, 0, 0])
    assert_array_equal(dummy_nexus_file[axis_entry + "_increment_set"][()], 1)
    # assert_array_equal(dummy_nexus_file[axis_entry + "_increment_set"][:], [1] * 3)
    assert dummy_nexus_file[axis_entry + "_end"][1] == 2


def test_given_module_offset_of_1_when_write_NXdetector_module_then_fast_and_slow_axis_depends_on_module_offset(
    dummy_nexus_file,
):
    test_module["module_offset"] = "1"
    write_NXdetector_module(
        dummy_nexus_file, test_module, "", [10, 10], [0.1, 0.1], [0, 0]
    )

    module_nexus_path = "/entry/instrument/detector/module/"
    for axis in ["slow_pixel_direction", "fast_pixel_direction"]:
        assert len(dummy_nexus_file[module_nexus_path + axis].attrs.keys()) == 6
        assert (
            dummy_nexus_file[module_nexus_path + axis].attrs["depends_on"]
            == b"/entry/instrument/detector/module/module_offset"
        )


def test_write_NXdatetime_from_IS8601str(dummy_nexus_file):
    # Check that ISO8601 strings are accepted and written to file
    entry_path = "/entry/"
    timestamps_str = ("2022-03-31T10:30:42Z", "2022-03-31T10:42:20Z")
    write_NXdatetime(dummy_nexus_file, timestamps_str)

    assert "start_time" in dummy_nexus_file[entry_path].keys()
    assert "end_time" in dummy_nexus_file[entry_path].keys()


def test_write_NXdatetime_from_datetime(dummy_nexus_file):
    # Check that datetime objects are accepted and written to file
    entry_path = "/entry/"
    start = datetime.fromisoformat("2022-03-31T16:30:32")
    stop = datetime.fromisoformat("2022-03-31T16:34:12")
    timestamps = (start, stop)
    write_NXdatetime(dummy_nexus_file, timestamps)

    assert "start_time" in dummy_nexus_file[entry_path].keys()
    assert "end_time" in dummy_nexus_file[entry_path].keys()


def test_write_NXdatetime_with_missing_timestamp(dummy_nexus_file):
    # Check that relevant dataset doesn't get written is timestamp is missing
    entry_path = "/entry/"
    timestamp = (None, "2022-04-01T09:40:56")
    write_NXdatetime(dummy_nexus_file, timestamp)

    assert "start_time" not in dummy_nexus_file[entry_path].keys()
    assert "end_time" in dummy_nexus_file[entry_path].keys()
    end = dummy_nexus_file[entry_path + "end_time"][()].decode()
    assert end.endswith("Z")
