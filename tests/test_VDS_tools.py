from nexgen.tools.VDS_tools import (
    get_start_idx_and_shape_per_dataset,
    create_virtual_layout,
)
import pytest
import numpy as np


def test_when_get_frames_and_shape_less_than_1000_then_correct():
    sshape = get_start_idx_and_shape_per_dataset((500, 10, 10))
    assert sshape == [(0, (500, 10, 10))]


def test_when_get_frames_and_shape_greater_than_1000_then_correct():
    sshape = get_start_idx_and_shape_per_dataset((1300, 10, 10))
    assert sshape == [(0, (1000, 10, 10)), (0, (300, 10, 10))]


def test_when_get_frames_and_shape_less_than_1000_non_zero_then_correct():
    sshape = get_start_idx_and_shape_per_dataset((500, 10, 10), 200)
    assert sshape == [(200, (500, 10, 10))]


def test_when_get_frames_and_shape_greater_than_1000_non_zero_then_correct():
    sshape = get_start_idx_and_shape_per_dataset((1500, 10, 10), 200)
    assert sshape == [(200, (1000, 10, 10)), (0, (500, 10, 10))]


def test_when_get_frames_and_shape_greater_than_1000_non_zero_greater_than_1000_then_correct():
    sshape = get_start_idx_and_shape_per_dataset((1500, 10, 10), 1200)
    assert sshape == [(1000, (1000, 10, 10)), (200, (500, 10, 10))]


def test_when_get_frames_and_shape_much_greater_than_1000_non_zero_greater_than_1000_then_correct():
    returned = get_start_idx_and_shape_per_dataset((3100, 10, 10), 1100)
    assert returned == [
        (1000, (1000, 10, 10)),
        (100, (1000, 10, 10)),
        (0, (1000, 10, 10)),
        (0, (100, 10, 10)),
    ]


def test_when_start_idx_higher_than_full_then_exception_raised():
    with pytest.raises(ValueError):
        get_start_idx_and_shape_per_dataset((1100, 10, 10), 3100)


def test_when_start_idx_negative_then_exception_raised():
    with pytest.raises(ValueError):
        get_start_idx_and_shape_per_dataset((1100, 10, 10), -100)


def test_create_virtual_layout_with_non_zero_start_and_greater_than_1000_images():
    create_virtual_layout(
        (1500, 10, 10),
        ["test_01", "test_02"],
        [(200, (1000, 10, 10)), (0, (500, 10, 10))],
        np.uint16,
        200,
    )


def test_create_virtual_layout():
    create_virtual_layout(
        (500, 10, 10),
        ["test_01"],
        [(0, (500, 10, 10))],
        np.uint16,
        0,
    )
