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


# @pytest.fixture
# def nexus_file_with_multiple_datasets():
#     with tempfile.TemporaryDirectory() as tmpdir:
#         data_path = Path(tmpdir) / "data.h5"
#         with h5py.File(data_path, "w") as fh:
#             fh.create_dataset("data", data=np.zeros((5, 2, 3)))
#             fh.flush()

#         test_hdf_file = tempfile.TemporaryFile()
#         test_nexus_file = h5py.File(test_hdf_file, "r+")
#         test_nexus_file.require_group("/entry/data")
#         test_nexus_file["/entry/data/data_0001"] = h5py.ExternalLink(
#             str(data_path), "data"
#         )
#         test_nexus_file["/entry/data/data_0002"] = h5py.ExternalLink(
#             str(data_path), "data"
#         )

#         yield test_nexus_file


@pytest.fixture(scope="session")
def nexus_file_with_multiple_datasets():
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as test_data_file:
        # data_path = Path(tmpdir) / "data.h5"
        with h5py.File(test_data_file.name, "w") as fh:
            fh.create_dataset("data", data=np.zeros((5, 2, 3)))
            fh.flush()

        test_hdf_file = tempfile.TemporaryFile()
        test_nexus_file = h5py.File(test_hdf_file, "r+")
        test_nexus_file.require_group("/entry/data")
        test_nexus_file["/entry/data/data_0001"] = h5py.ExternalLink(
            test_data_file.name, "data"
        )
        test_nexus_file["/entry/data/data_0002"] = h5py.ExternalLink(
            test_data_file.name, "data"
        )

        yield test_nexus_file

        # test_data_file.close()
