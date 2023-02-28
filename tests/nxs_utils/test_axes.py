from numpy.testing import assert_array_equal

from nexgen.nxs_utils import Point3D
from nexgen.nxs_utils.Axes import Axis

test_rot_axis = Axis("omega", ".", "rotation", Point3D(0, 0, -1), -90)
test_transl_axis = Axis("sam_x", "omega", "translation", (1, 0, 0), 0, 0.1, 10)


def test_axes():
    assert test_rot_axis.name == "omega"
    assert test_rot_axis.start_pos == -90

    assert test_transl_axis.name == "sam_x"
    assert test_transl_axis.depends == "omega"
    assert_array_equal(test_transl_axis.vector, (1, 0, 0))


def test_axis_units():
    assert test_rot_axis.transformation_type == "rotation"
    assert test_rot_axis.units == "deg"

    assert test_transl_axis.transformation_type == "translation"
    assert test_transl_axis.units == "mm"


def test_axis_with_Point3D_vector_input():
    assert type(test_rot_axis.vector) is tuple
    assert_array_equal(test_rot_axis.vector, (0, 0, -1))


def test_axis_is_scan():
    assert test_rot_axis.is_scan is False
    assert test_transl_axis.is_scan is True


def test_axis_end_pos():
    assert test_rot_axis.end_pos == test_rot_axis.start_pos
    assert test_transl_axis.end_pos == 1.0
