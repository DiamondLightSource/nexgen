import pytest

from nexgen.command_line.cli_utils import (
    reframe_arrays,
    set_detector_params,
    split_arrays,
)
from nexgen.nxs_utils.detector import UnknownDetectorTypeError

test_goniometer_small = {
    "axes": ["alpha", "sam_z"],
    "vectors": [1, 0, 0, 0, 0, 1],
    "offsets": [(0, 0, 0), (0, 0, 0)],
}

test_detector = {"axes": ["det_z"], "vectors": [0, 0, 1]}
test_module = {
    "fast_axis": [1, 0, 0],
    "slow_axis": [0, 1, 0],
}

test_new_coords = {
    "convention": "rotate",
    "origin": (0, 0, 0),
    "x": (".", "", "", [1, 0, 0]),
    "y": (".", "", "", [0, -1, 0]),
    "z": (".", "", "", [0, 0, -1]),
}


def test_reframe_arrays_without_coordinate_conversion():
    reframe_arrays(
        test_goniometer_small,
        test_detector,
        test_module,
    )
    assert test_goniometer_small["vectors"] == [(1, 0, 0), (0, 0, 1)]
    assert test_detector["vectors"] == [(0, 0, 1)]


def test_reframe_arrays_from_imgcif():
    reframe_arrays(
        test_goniometer_small,
        test_detector,
        test_module,
        "imgcif",
    )
    assert test_goniometer_small["vectors"] == [(-1, 0, 0), (0, 0, -1)]
    assert test_detector["vectors"] == [(0, 0, -1)]
    assert test_module["fast_axis"] == (-1, 0, 0)
    assert test_module["slow_axis"] == (0, 1, 0)


def test_reframe_arrays_from_another_coordinate_system():
    test_goniometer_small["vectors"] = [1, 0, 0, 0, 0, 1]
    test_detector["vectors"] = [0, 0, 1]
    test_module["fast_axis"] = [1, 0, 0]
    test_module["slow_axis"] = [0, 1, 0]
    test_module["offsets"] = [0, 0, 0, 0, 0, 0]
    reframe_arrays(
        test_goniometer_small,
        test_detector,
        test_module,
        "rotate",
        test_new_coords,
    )

    assert test_goniometer_small["vectors"] == [(1, 0, 0), (0, 0, -1)]
    assert test_detector["vectors"] == [(0, 0, -1)]
    assert test_module["fast_axis"] == (1, 0, 0)
    assert test_module["slow_axis"] == (0, -1, 0)
    assert test_module["offsets"] == [(0, 0, 0), (0, 0, 0)]


def test_reframe_arrays_fails_if_coordinate_system_ill_defined():
    with pytest.raises(ValueError):
        reframe_arrays(
            test_goniometer_small, test_detector, test_module, "", test_new_coords
        )


def test_reframe_arrays_fails_if_new_coordinate_system_not_defined():
    with pytest.raises(TypeError):
        reframe_arrays(test_goniometer_small, test_detector, test_module, "new")


def test_split_arrays():
    assert split_arrays(["phi"], [1, 0, 0]) == {"phi": (1, 0, 0)}
    two_axes = split_arrays(["omega", "phi"], [1, 0, 0, 0, 1, 0])
    assert two_axes["omega"] == (1, 0, 0) and two_axes["phi"] == (0, 1, 0)
    assert (
        len(split_arrays(["omega", "phi", "chi"], [(1, 0, 0), (0, 1, 0), (0, 0, 1)]))
        == 3
    )


def test_split_arrays_fails_if_wrong_size_arrays():
    with pytest.raises(ValueError):
        split_arrays(["omega", "phi"], [1, 0, 0, 1])


def test_set_detector_params_fails_if_missing_kwargs():
    with pytest.raises(ValueError):
        set_detector_params("tristan", image_size=[1, 2])


def test_set_detector_params_fails_if_neither_tristan_nor_eiger():
    with pytest.raises(UnknownDetectorTypeError):
        set_detector_params("singla")
