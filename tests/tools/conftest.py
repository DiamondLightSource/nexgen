import tempfile

import h5py
import pytest


@pytest.fixture
def nexus_file_with_single_dataset():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    test_nexus_file["/entry/data/data_0001"] = h5py.ExternalLink("filename", "data")
    yield test_nexus_file


@pytest.fixture(scope="session")
def nexus_file_with_multiple_datasets():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "r+")
    test_nexus_file.require_group("/entry/data")
    test_nexus_file["/entry/data/data_0001"] = h5py.ExternalLink("file_1", "data")
    test_nexus_file["/entry/data/data_0002"] = h5py.ExternalLink("file_2", "data")

    yield test_nexus_file
