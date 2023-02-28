import pytest

from nexgen.nxs_utils.Axes import Axis
from nexgen.nxs_utils.ScanUtils import identify_grid_scan_axes, identify_osc_axis

test_axis_list = [
    Axis("omega", ".", "rotation", (0, 0, -1), -90),
    Axis("phi", "omega", "rotation", (0, 0, -1), 180),
    Axis("sam_y", "phi", "translation", (1, 0, 0), 0, 0.1, 10),
    Axis("sam_x", "sam_y", "translation", (0, 1, 0), 0, 0.2, 10),
]


def test_identify_osc_axis():
    osc_axis = identify_osc_axis(
        [
            Axis("chi", ".", "rotation", (0, 0, -1), -90, 0.1, 100),
            Axis("phi", "chi", "rotation", (0, 0, -1), 180),
        ]
    )
    assert osc_axis == "chi"


def test_identify_osc_axis_with_just_one_rotation_axis():
    osc_axis = identify_osc_axis([Axis("phi", "omega", "rotation", (0, 0, -1), 180)])
    assert osc_axis == "phi"


def test_identify_osc_axis_from_default_value():
    osc_axis = identify_osc_axis(test_axis_list, default="omega")
    assert osc_axis == "omega"


def test_identify_grid_scan_axis():
    grid_axes = identify_grid_scan_axes(test_axis_list)
    assert "sam_x" in grid_axes
    assert "sam_y" in grid_axes


def test_osc_axis_search_fails_for_multiple_moving_axes():
    with pytest.raises(ValueError):
        identify_osc_axis(
            [
                Axis("chi", ".", "rotation", (0, 0, -1), -90, 0.1, 100),
                Axis("phi", "chi", "rotation", (0, 0, -1), 180, 0.5, 50),
            ]
        )


def test_osc_axis_search_fails_for_no_axes():
    with pytest.raises(ValueError):
        identify_osc_axis([])


def test_grid_axis_search_fails_for_no_axes():
    with pytest.raises(ValueError):
        identify_grid_scan_axes([])
