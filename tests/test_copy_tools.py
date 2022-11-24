import tempfile

import h5py
import pytest

from nexgen.nxs_copy import find_chipmap_in_tristan_nxs
from nexgen.nxs_write.NXclassWriters import write_NXentry, write_NXnote

test_chipmap = {"01": (0, 0)}


@pytest.fixture
def dummy_nexus_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    yield test_nexus_file


def test_find_chipmap(dummy_nexus_file):
    test_map = {"chipmap": str(test_chipmap)}
    nxentry = write_NXentry(dummy_nexus_file)
    write_NXnote(dummy_nexus_file, "/entry/source/notes", test_map)

    assert find_chipmap_in_tristan_nxs(dummy_nexus_file) is True
    assert find_chipmap_in_tristan_nxs(nxentry, loc="source/notes/chipmap") is True
