import nexgen

import pint
import time

ureg = pint.UnitRegistry()


def test_cif2nxs():
    assert nexgen.imgcif2mcstas([0, 0, 0]) == (0, 0, 0)
    assert nexgen.imgcif2mcstas([1, 0, 0]) == (-1, 0, 0)
    assert nexgen.imgcif2mcstas([0, 1, 0]) == (0, 1, 0)
    assert nexgen.imgcif2mcstas([0, 0, 1]) == (0, 0, -1)


def test_iso_timestamps():
    assert nexgen.get_iso_timestamp(None) is None
    # Check that no exceptions are raised when passing a time.time() object
    assert nexgen.get_iso_timestamp(time.time())


def test_units_of_length():
    assert nexgen.units_of_length("1.5m") == ureg.Quantity(1.5, "m")
    # Check that a dimensionless unit defaults to mm
    assert nexgen.units_of_length(100) == ureg.Quantity(100, "m")
    # Check conversion to base units
    assert nexgen.units_of_length("5cm", True) == ureg.Quantity(0.05, "m")
    assert nexgen.units_of_length("1in", True) == ureg.Quantity(0.0254, "m")


def test_units_of_time():
    assert nexgen.units_of_time("0.05s") == ureg.Quantity(0.05, "s")
    # Check that a dimensionless value deafults to seconds
    assert nexgen.units_of_time(1) == ureg.Quantity(1, "s")
    # Check conversion to base units
    assert nexgen.units_of_time("20ms") == ureg.Quantity(0.02, "s")
