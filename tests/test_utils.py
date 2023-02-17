import time

import pint
import pytest

from nexgen import utils

ureg = pint.UnitRegistry()


def test_iso_timestamps():
    assert utils.get_iso_timestamp(None) is None
    # Check that no exceptions are raised when passing a time.time() object
    assert utils.get_iso_timestamp(time.time())


def test_units_of_length():
    assert utils.units_of_length("1.5m") == ureg.Quantity(1.5, "m")
    # Check that a dimensionless unit defaults to mm
    assert utils.units_of_length(100) == ureg.Quantity(100, "m")
    # Check conversion to base units
    assert utils.units_of_length("5cm", True) == ureg.Quantity(0.05, "m")
    assert utils.units_of_length("1in", True) == ureg.Quantity(0.0254, "m")


def test_units_of_length_raises_error_for_wrong_dimension():
    with pytest.raises(pint.errors.DimensionalityError):
        utils.units_of_length("30s")


def test_units_of_time():
    assert utils.units_of_time("0.05s") == ureg.Quantity(0.05, "s")
    # Check that a dimensionless value deafults to seconds
    assert utils.units_of_time(1) == ureg.Quantity(1, "s")
    # Check conversion to base units
    assert utils.units_of_time("20ms") == ureg.Quantity(0.02, "s")


def test_units_of_time_raises_error_for_wrong_dimension():
    with pytest.raises(pint.errors.DimensionalityError):
        utils.units_of_time("0.2in")
