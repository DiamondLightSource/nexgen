import numpy as np

# import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_utils import Axis, Goniometer

axes_list = [
    Axis("omega", ".", "rotation", (0, 0, -1), 0.0),
    Axis("sam_z", "omega", "translation", (0, 0, 1), 0.0),
    Axis("sam_y", "sam_z", "translation", (0, 1, 0), 0.0, 0.1, 10),
    Axis("sam_x", "sam_y", "translation", (1, 0, 0), 0.0, 0.1, 10),
]


def test_goniometer_to_dict():
    gonio = Goniometer(axes_list[:2]).to_dict()
    assert type(gonio) is dict
    assert gonio["axes"] == ["omega", "sam_z"]
    assert gonio["depends"] == [".", "omega"]
    assert gonio["vectors"] == [(0, 0, -1), (0, 0, 1)]
    assert gonio["types"] == ["rotation", "translation"]
    assert gonio["units"] == ["deg", "mm"]


def test_define_scan_from_gonio():
    osc_scan, grid_scan = Goniometer(axes_list).define_scan_from_goniometer_axes()
    assert_array_equal(osc_scan["omega"], np.repeat(0.0, 100))
    assert "sam_x" in list(grid_scan.keys()) and "sam_y" in list(grid_scan.keys())
    assert grid_scan["sam_y"][0] == 0.0
    assert grid_scan["sam_y"][-1] == 0.9
    assert np.min(grid_scan["sam_x"]) == 0.0 and np.max(grid_scan["sam_x"]) == 0.9
    assert round(grid_scan["sam_x"][1] - grid_scan["sam_x"][0], 1) == 0.1


def test_define_scan_given_a_rotation_scan():
    scan = {"omega": np.arange(0, 10, 1)}
    osc_scan, grid_scan = Goniometer(axes_list, scan).define_scan_from_goniometer_axes()
    assert grid_scan is None
    assert_array_equal(osc_scan["omega"], scan["omega"])


def test_define_scan_given_a_grid_scan():
    # Whatever scan is passed overrides the gonio definition.
    scan = {
        "sam_y": np.array([0, 0, 0, 1, 1, 1]),
        "sam_x": np.array([0, 1, 2, 2, 1, 0]),
    }
    osc_scan, grid_scan = Goniometer(axes_list, scan).define_scan_from_goniometer_axes()
    assert osc_scan is not None
    assert_array_equal(osc_scan["omega"], np.repeat(0.0, 6))
    assert "sam_x" in list(grid_scan.keys()) and "sam_y" in list(grid_scan.keys())
    assert_array_equal(grid_scan["sam_y"], scan["sam_y"])
    assert_array_equal(grid_scan["sam_x"], scan["sam_x"])


def test_define_scan_axes_for_event_mode_given_scan():
    scan = {"omega": (-90, 0)}
    osc_scan, grid_scan = Goniometer(axes_list, scan).define_scan_axes_for_event_mode()
    assert grid_scan is None
    assert_array_equal(osc_scan["omega"], scan["omega"])


def test_define_scan_axes_for_event_mode():
    osc_scan, _ = Goniometer(axes_list).define_scan_axes_for_event_mode()
    assert_array_equal(osc_scan["omega"], (0, 0))


def test_define_scan_axes_for_event_mode_given_new_end_position():
    osc_scan, _ = Goniometer(axes_list).define_scan_axes_for_event_mode(
        end_position=180
    )
    assert_array_equal(osc_scan["omega"], (0, 180))
