from nexgen.tools.VDS_tools import (
    Dataset,
    split_datasets,
    create_virtual_layout,
)
import pytest
import numpy as np


def test_when_get_frames_and_shape_less_than_1000_then_correct():
    sshape = split_datasets(["test1"], (500, 10, 10))
    assert sshape == [Dataset("test1", (500, 10, 10), 0)]

    create_virtual_layout(sshape, np.uint16)


def test_when_get_frames_and_shape_greater_than_1000_then_correct():
    sshape = split_datasets(["test1", "test2"], (1300, 10, 10))
    assert sshape == [
        Dataset("test1", (1000, 10, 10), 0),
        Dataset("test2", (300, 10, 10), 0),
    ]

    create_virtual_layout(sshape, np.uint16)


def test_when_get_frames_and_shape_less_than_1000_non_zero_then_correct():
    sshape = split_datasets(["test1"], (500, 10, 10), 200)
    assert sshape == [Dataset("test1", (500, 10, 10), 200)]

    create_virtual_layout(sshape, np.uint16)


def test_when_get_frames_and_shape_greater_than_1000_non_zero_then_correct():
    sshape = split_datasets(["test1", "test2"], (1500, 10, 10), 200)
    assert sshape == [
        Dataset("test1", (1000, 10, 10), 200),
        Dataset("test2", (500, 10, 10), 0),
    ]

    create_virtual_layout(sshape, np.uint16)


def test_when_get_frames_and_shape_greater_than_1000_non_zero_greater_than_1000_then_correct():
    sshape = split_datasets(["test1", "test2"], (1500, 10, 10), 1200)
    assert sshape == [
        Dataset("test1", (1000, 10, 10), 1000),
        Dataset("test2", (500, 10, 10), 200),
    ]

    create_virtual_layout(sshape, np.uint16)


def test_when_get_frames_and_shape_much_greater_than_1000_non_zero_greater_than_1000_then_correct():
    returned = split_datasets(
        ["test1", "test2", "test3", "test4"], (3100, 10, 10), 1100
    )
    assert returned == [
        Dataset("test1", (1000, 10, 10), 1000),
        Dataset("test2", (1000, 10, 10), 100),
        Dataset("test3", (1000, 10, 10), 0),
        Dataset("test4", (100, 10, 10), 0),
    ]

    create_virtual_layout(returned, np.uint16)


def test_when_start_idx_higher_than_full_then_exception_raised():
    with pytest.raises(ValueError):
        split_datasets(["test1", "test2"], (1100, 10, 10), 3100)


def test_when_start_idx_negative_then_exception_raised():
    with pytest.raises(ValueError):
        split_datasets(["test1"], (1100, 10, 10), -100)
