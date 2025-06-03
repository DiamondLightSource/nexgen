import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_utils import Axis, Goniometer, TransformationType


@pytest.fixture
def axes_list() -> list[Axis]:
    return [
        Axis("omega", ".", TransformationType.ROTATION, (0, 0, -1), 0.0),
        Axis("sam_z", "omega", TransformationType.TRANSLATION, (0, 0, 1), 0.0),
        Axis("sam_y", "sam_z", TransformationType.TRANSLATION, (0, 1, 0), 0.0, 0.1, 10),
        Axis("sam_x", "sam_y", TransformationType.TRANSLATION, (1, 0, 0), 0.0, 0.1, 10),
    ]


def test_define_scan_from_gonio(axes_list):
    osc_scan, grid_scan = Goniometer(axes_list).define_scan_from_goniometer_axes()
    assert_array_equal(osc_scan["omega"], np.repeat(0.0, 100))
    assert "sam_x" in list(grid_scan.keys()) and "sam_y" in list(grid_scan.keys())
    assert grid_scan["sam_y"][0] == 0.0
    assert grid_scan["sam_y"][-1] == 0.9
    assert np.min(grid_scan["sam_x"]) == 0.0 and np.max(grid_scan["sam_x"]) == 0.9
    assert round(grid_scan["sam_x"][1] - grid_scan["sam_x"][0], 1) == 0.1


def test_define_scan_given_a_rotation_scan(axes_list):
    scan = {"omega": np.arange(0, 10, 1)}
    osc_scan, grid_scan = Goniometer(axes_list, scan).define_scan_from_goniometer_axes()
    assert grid_scan is None
    assert_array_equal(osc_scan["omega"], scan["omega"])


def test_define_scan_given_a_grid_scan(axes_list):
    # For testing pusposes, reset number of images for omega
    axes_list[0].num_steps = 0
    axes_list[0].increment = 0
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


def test_get_number_of_scan_points_given_a_scan(axes_list):
    scan = {
        "sam_y": np.array([0, 0, 0, 1, 1, 1]),
        "sam_x": np.array([0, 1, 2, 2, 1, 0]),
    }
    num_frames = Goniometer(axes_list, scan).get_number_of_scan_points()
    assert num_frames == len(scan["sam_x"])


def test_get_number_of_scan_points():
    num_frames = Goniometer(
        [
            Axis("omega", ".", TransformationType.ROTATION, (0, 0, -1), 90.0),
            Axis("phi", "omega", TransformationType.ROTATION, (0, 0, -1), 0.0, 0.2, 10),
        ],
    ).get_number_of_scan_points()
    assert num_frames == 10


def test_define_scan_axes_for_event_mode_given_scan():
    scan = {"phi": (-90, 0)}
    osc_scan, grid_scan = Goniometer(
        [Axis("phi", ".", TransformationType.ROTATION, (0, 0, -1), 0.0)], scan
    ).define_scan_axes_for_event_mode()
    assert grid_scan is None
    assert_array_equal(osc_scan["phi"], scan["phi"])


def test_define_scan_axes_for_event_mode(axes_list):
    osc_scan, _ = Goniometer(
        [Axis("phi", ".", TransformationType.ROTATION, (0, 0, -1), 0.0), *axes_list[1:]]
    ).define_scan_axes_for_event_mode()
    assert_array_equal(osc_scan["phi"], (0, 0))


def test_define_scan_axes_for_event_mode_given_new_end_position(axes_list):
    osc_scan, _ = Goniometer(axes_list).define_scan_axes_for_event_mode(
        end_position=180
    )
    assert_array_equal(osc_scan["omega"], (0, 180))


def test_given_scan_gonio_positions_correctly_updated(axes_list):
    scan = {
        "sam_y": np.repeat(np.arange(0, 1.0, 0.2), 2),
        "sam_x": np.array(np.tile([1.0, 2.0], 5)),
    }
    _, _ = Goniometer(axes_list, scan).define_scan_from_goniometer_axes()
    Xidx, Yidx = (3, 2)
    assert axes_list[Xidx].start_pos != 0.0
    assert axes_list[Xidx].start_pos == 1.0 and axes_list[Xidx].end_pos == 2.0
    assert axes_list[Yidx].start_pos == 0.0 and axes_list[Yidx].end_pos == 0.8
    assert axes_list[Yidx].increment == 0.2 and axes_list[Xidx].increment == 1.0
    assert axes_list[Xidx].num_steps == 2 and axes_list[Yidx].num_steps == 5


def test_gonio_axes_have_correct_values_if_given_forward_or_reverse_rotation_scan(
    axes_list,
):
    # Forward scan
    scan_fw = {"omega": np.arange(1, 2, 0.1)}
    gonio_fw = Goniometer(axes_list, scan_fw)
    # Omega first acxis in list
    assert gonio_fw.axes_list[0].start_pos == 1.0
    assert gonio_fw.axes_list[0].increment == 0.1
    assert gonio_fw.axes_list[0].num_steps == 10

    # Reverse scan
    scan_rw = {"omega": np.arange(7.5, 7, -0.1)}
    gonio_rw = Goniometer(axes_list, scan_rw)
    assert gonio_rw.axes_list[0].start_pos == 7.5
    assert gonio_rw.axes_list[0].increment == -0.1
    assert gonio_rw.axes_list[0].num_steps == 5
