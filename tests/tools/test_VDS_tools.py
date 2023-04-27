import tempfile
from unittest.mock import MagicMock

import h5py
import numpy as np
import pytest

from nexgen.tools.VDS_tools import (
    Dataset,
    create_virtual_layout,
    image_vds_writer,
    split_datasets,
)


def test_when_get_frames_and_shape_less_than_1000_then_correct():
    sshape = split_datasets(["test1"], (500, 10, 10))
    assert sshape == [Dataset("test1", (500, 10, 10), 0, 500)]

    create_virtual_layout(sshape, np.uint16)


def test_when_get_frames_and_shape_greater_than_1000_then_correct():
    sshape = split_datasets(["test1", "test2"], (1300, 10, 10))
    assert sshape == [
        Dataset("test1", (1000, 10, 10), 0, 1000),
        Dataset("test2", (300, 10, 10), 0, 300),
    ]

    create_virtual_layout(sshape, np.uint16)


def test_when_get_frames_and_shape_less_than_1000_non_zero_then_correct():
    sshape = split_datasets(["test1"], (500, 10, 10), 200, (300, 10, 10))
    assert sshape == [Dataset("test1", (500, 10, 10), 200, 500)]

    create_virtual_layout(sshape, np.uint16)


def test_when_get_frames_and_shape_greater_than_1000_non_zero_then_correct():
    sshape = split_datasets(["test1", "test2"], (1500, 10, 10), 200)
    assert sshape == [
        Dataset("test1", (1000, 10, 10), 200, 1000),
        Dataset("test2", (500, 10, 10), 0, 500),
    ]

    create_virtual_layout(sshape, np.uint16)


def test_when_get_frames_and_shape_greater_than_1000_non_zero_greater_than_1000_then_correct():
    sshape = split_datasets(["test1", "test2"], (1500, 10, 10), 1200)
    assert sshape == [
        Dataset("test2", (500, 10, 10), 200, 500),
    ]

    create_virtual_layout(sshape, np.uint16)


def test_when_get_frames_and_shape_much_greater_than_1000_non_zero_greater_than_1000_then_correct():
    returned = split_datasets(
        ["test1", "test2", "test3", "test4"], (3100, 10, 10), 1100
    )
    assert returned == [
        Dataset("test2", (1000, 10, 10), 100, 1000),
        Dataset("test3", (1000, 10, 10), 0, 1000),
        Dataset("test4", (100, 10, 10), 0, 100),
    ]

    create_virtual_layout(returned, np.uint16)


def test_when_start_idx_higher_than_full_then_exception_raised():
    with pytest.raises(ValueError):
        split_datasets(["test1", "test2"], (1100, 10, 10), 3100)


def test_when_start_idx_negative_then_exception_raised():
    with pytest.raises(ValueError):
        split_datasets(["test1"], (1100, 10, 10), -100)


@pytest.fixture
def nexus_file_with_single_dataset():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    test_nexus_file["/entry/data/data_0001"] = h5py.ExternalLink("filename", "path")
    yield test_nexus_file


def test_when_float_shape_passed_to_vds_writer_then_no_exception(
    nexus_file_with_single_dataset,
):
    image_vds_writer(nexus_file_with_single_dataset, (500.0, 10.0, 10.0), start_index=0)


def test_when_float_start_index_passed_to_vds_writer_then_no_exception(
    nexus_file_with_single_dataset,
):
    image_vds_writer(
        nexus_file_with_single_dataset, (500.0, 10.0, 10.0), start_index=0.0
    )


def test_given_file_with_no_dataset_external_links_then_exception_is_sensible():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    test_nexus_file["/entry/data/data_0001"] = MagicMock()
    with pytest.raises(KeyError):
        image_vds_writer(test_nexus_file, (1000, 10, 10))
