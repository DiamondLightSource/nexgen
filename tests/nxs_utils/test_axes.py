import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_utils.axes import Axis, TransformationType
from nexgen.utils import Point3D


@pytest.fixture
def rotation_axis() -> Axis:
    return Axis("omega", ".", TransformationType.ROTATION, Point3D(0, 0, -1), -90)


@pytest.fixture
def translation_axis() -> Axis:
    return Axis("sam_x", "omega", TransformationType.TRANSLATION, (1, 0, 0), 0, 0.1, 10)


def test_axes(rotation_axis, translation_axis):
    assert rotation_axis.name == "omega"
    assert rotation_axis.start_pos == -90

    assert translation_axis.name == "sam_x"
    assert translation_axis.depends == "omega"
    assert_array_equal(translation_axis.vector, (1, 0, 0))


def test_axis_units(rotation_axis, translation_axis):
    assert rotation_axis.transformation_type == "rotation"
    assert rotation_axis.units == "deg"

    assert translation_axis.transformation_type == "translation"
    assert translation_axis.units == "mm"


def test_axis_with_Point3D_vector_input(rotation_axis):
    assert type(rotation_axis.vector) is tuple
    assert_array_equal(rotation_axis.vector, (0, 0, -1))


def test_axis_is_scan(rotation_axis, translation_axis):
    assert rotation_axis.is_scan is False
    assert translation_axis.is_scan is True


def test_axis_start_pos(rotation_axis):
    assert rotation_axis.start_pos != 0.0
    assert rotation_axis.start_pos == -90.0
    test_rot_axis_2 = Axis("phi", ".", TransformationType.ROTATION, Point3D(0, 0, -1))
    assert test_rot_axis_2.start_pos == 0.0


def test_axis_end_pos(rotation_axis, translation_axis):
    assert rotation_axis.end_pos == rotation_axis.start_pos
    assert translation_axis.end_pos == 0.9
