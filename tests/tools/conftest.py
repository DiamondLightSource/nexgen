import tempfile

import h5py
import pytest


@pytest.fixture
def nexus_file_with_single_dataset():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    test_nexus_file["/entry/data/data_0001"] = h5py.ExternalLink("filename", "path")
    yield test_nexus_file
