import tempfile
import h5py
import pytest
from nexgen.nxs_write.NXclassWriters import write_NXdetector_module

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
