import tempfile

import h5py
import numpy as np
import pytest


@pytest.fixture
def nexus_file_with_single_dataset():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    test_nexus_file["/entry/data/data_0001"] = h5py.ExternalLink("filename", "data")
    yield test_nexus_file


@pytest.fixture(scope="session")
def dummy_data_file():
    test_data_file = tempfile.NamedTemporaryFile(suffix=".h5", delete=True)
    test_data_file.close()
    with h5py.File(test_data_file.name, "w") as fh:
        fh["data"] = np.zeros((10, 2, 3))
        fh.flush()
    yield test_data_file.name

    # os.remove(test_data_file.name)


@pytest.fixture
def nexus_file_with_multiple_datasets(dummy_data_file):
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    test_nexus_file["/entry/data/data_0001"] = h5py.ExternalLink(
        dummy_data_file, "data"
    )
    test_nexus_file["/entry/data/data_0002"] = h5py.ExternalLink(
        dummy_data_file, "data"
    )
    yield test_nexus_file
