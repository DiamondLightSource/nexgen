import tempfile
import h5py
import pytest

# from datetime import datetime
from nexgen.nxs_write.NXclassWriters import (
    write_NXdetector_module,
)  # , write_NXdatetime

test_module = {"fast_axis": [1, 0, 0], "slow_axis": [0, 1, 0]}


@pytest.fixture
def dummy_nexus_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    yield test_nexus_file


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


# def test_write_NXdatetime_from_IS8601str(dummy_nexus_file):
#     # Check that ISO8601 strings are accepted and written to file
#     entry_path = "/entry/"
#     timestamps_str = ("2022-03-31T10:30:42Z", "2022-03-31T10:42:20Z")
#     write_NXdatetime(dummy_nexus_file, timestamps_str)

#     assert "start_time" in dummy_nexus_file[entry_path].keys()
#     assert "end_time" in dummy_nexus_file[entry_path].keys()


# def test_write_NXdatetime_from_datetime(dummy_nexus_file):
#     # Check that datetime objects are accepted and written to file
#     entry_path = "/entry/"
#     start = datetime.fromisoformat("2022-03-31T16:30:32")
#     stop = datetime.fromisoformat("2022-03-31T16:34:12")
#     timestamps = (start, stop)
#     write_NXdatetime(dummy_nexus_file, timestamps)

#     assert "start_time" in dummy_nexus_file[entry_path].keys()
#     assert "end_time" in dummy_nexus_file[entry_path].keys()


# def test_write_NXdatetime_with_missing_timestamp(dummy_nexus_file):
#     # Check that relevant dataset doesn't get written is timestamp is missing
#     entry_path = "/entry/"
#     timestamp = (None, "2022-04-01T09:40:56")
#     write_NXdatetime(dummy_nexus_file, timestamp)

#     assert "start_time" not in dummy_nexus_file[entry_path].keys()
#     assert "end_time" in dummy_nexus_file[entry_path].keys()
#     end = dummy_nexus_file[entry_path + "end_time"][()].decode()
#     assert end.endswith("Z")
