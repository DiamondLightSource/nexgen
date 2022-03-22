from nexgen.nxs_write import calculate_scan_range, calculate_scan_from_scanspec
import numpy as np
from scanspec.specs import Line


def test_given_start_stop_and_increment_when_calculate_scan_range_called_then_expected_range_returned():
    start = 0
    stop = 10
    increment = 0.25
    scan_range = calculate_scan_range(start, stop, increment)
    assert type(scan_range) == np.ndarray
    assert len(scan_range) == 40
    assert np.amax(scan_range) == 9.75
    assert np.amin(scan_range) == 0
    assert scan_range[3] == 0.75


def test_given_start_stop_and_n_images_when_calculate_scan_range_called_then_expected_range_returned():
    start = 0
    stop = 10
    n_images = 41
    scan_range = calculate_scan_range(start, stop, n_images=n_images)
    assert type(scan_range) == np.ndarray
    assert len(scan_range) == 41
    assert np.amax(scan_range) == 10.0
    assert np.amin(scan_range) == 0
    assert scan_range[3] == 0.75


def test_given_equal_start_stop_and_n_images_when_calculate_scan_range_called_then_expected_range_returned():
    start = 2
    stop = 2
    n_images = 41
    scan_range = calculate_scan_range(start, stop, n_images=n_images)
    assert type(scan_range) == np.ndarray
    assert len(scan_range) == 41
    assert np.amax(scan_range) == 2.0
    assert np.amin(scan_range) == 2.0
    assert scan_range[3] == 2.0


def test_calculate_from_scanspec():
    spec = Line("x", 0, 10, 41)
    midpoints = calculate_scan_from_scanspec(spec)
    scan_range = midpoints["x"]
    assert type(scan_range) == np.ndarray
    assert len(scan_range) == 41
    assert np.amax(scan_range) == 10.0
    assert np.amin(scan_range) == 0
    assert scan_range[3] == 0.75
