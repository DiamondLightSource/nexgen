import tempfile

import h5py
import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_copy import h5str, identify_tristan_scan_axis, is_chipmap_in_tristan_nxs
from nexgen.nxs_write import create_attributes
from nexgen.nxs_write.NXclassWriters import write_NXentry, write_NXnote

test_chipmap = {"01": (0, 0)}


def test_h5str():
    assert h5str("string_obj") == "string_obj"
    assert h5str(b"bytes_obj") == "bytes_obj"


@pytest.fixture
def dummy_nexus_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    yield test_nexus_file


def test_identify_tristan_scan_axis(dummy_nexus_file):
    nxentry = write_NXentry(dummy_nexus_file)
    nxdata = nxentry.require_group("data")
    axis1 = nxdata.create_dataset("omega", data=(0, 0))
    create_attributes(
        axis1, ("transformation_type", "vector"), (b"rotation", [0, 0, 1])
    )
    axis2 = nxdata.create_dataset("sam_x", data=(0,))
    create_attributes(axis2, ("transformation_type",), ("translation",))
    nxdata.create_dataset("data", data=b"Some dummy data")

    ax, ax_attrs = identify_tristan_scan_axis(dummy_nexus_file)
    assert ax == "omega"
    assert len(ax_attrs) > 0
    assert ax_attrs["transformation_type"] == "rotation"
    assert_array_equal(ax_attrs["vector"], [0, 0, 1])


def test_find_chipmap(dummy_nexus_file):
    test_map = {"chipmap": str(test_chipmap)}
    nxentry = write_NXentry(dummy_nexus_file)
    write_NXnote(dummy_nexus_file, "/entry/source/notes", test_map)

    assert is_chipmap_in_tristan_nxs(dummy_nexus_file) is True
    assert is_chipmap_in_tristan_nxs(nxentry, loc="source/notes/chipmap") is True
