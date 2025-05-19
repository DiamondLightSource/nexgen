import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pint
import pytest

from nexgen import utils

ureg = pint.UnitRegistry()


def test_cif2nxs():
    assert utils.imgcif2mcstas([0, 0, 0]) == (0, 0, 0)
    assert utils.imgcif2mcstas([1, 0, 0]) == (-1, 0, 0)
    assert utils.imgcif2mcstas([0, 1, 0]) == (0, 1, 0)
    assert utils.imgcif2mcstas([0, 0, 1]) == (0, 0, -1)


def test_coord2nxs():
    R = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    assert utils.coord2mcstas([0, 0, 0], R) == (0, 0, 0)
    assert utils.coord2mcstas([1, 0, 0], R) == (1, 0, 0)
    assert utils.coord2mcstas([0, 1, 0], R) == (0, 0, 1)
    assert utils.coord2mcstas([0, 0, 1], R) == (0, -1, 0)


def test_coerce_to_path():
    s = "/some/path"
    s = utils.coerce_to_path(s)
    assert isinstance(s, Path)


def test_find_in_dict():
    test_dict = {
        "alpha": 0,
        "beta": 1,
    }
    assert utils.find_in_dict("alpha", test_dict) is True
    assert utils.find_in_dict("gamma", test_dict) is False


def test_get_filename_template():
    # Check filename from _master.h5 file
    fn = utils.get_filename_template(Path("File_01_master.h5"))
    assert isinstance(fn, str)
    assert fn == "File_01_%06d.h5"
    assert fn % 1 == "File_01_000001.h5"
    # Check filename from .nxs file
    fn = utils.get_filename_template(Path("File_02.nxs"))
    assert isinstance(fn, str)
    assert fn == "File_02_%06d.h5"
    assert fn % 1 == "File_02_000001.h5"


def test_get_nexus_filename():
    # Check nexus filename from meta
    nxs = utils.get_nexus_filename(Path("File_01_meta.h5"))
    assert nxs.as_posix() == "File_01.nxs"
    # Check nexus filename from datafile
    nxs = utils.get_nexus_filename(Path("File_02_0001.h5"))
    assert nxs.as_posix() == "File_02.nxs"


def test_iso_timestamps():
    assert utils.get_iso_timestamp(None) is None
    # Check that no exceptions are raised when passing a time.time() object
    assert utils.get_iso_timestamp(time.time())


def test_iso_timestamps_fails_for_wrong_input_type():
    with pytest.raises(ValueError):
        utils.get_iso_timestamp(datetime.now())


@pytest.mark.parametrize(
    "ts, expected_iso",
    [
        ("2023-10-15T20:12:26", "2023-10-15T20:12:26Z"),
        ("2024-03-12 11:35:01", "2024-03-12T11:35:01Z"),
        ("Mon May 19 2025 10:45:28", "2025-05-19T10:45:28Z"),
    ],
)
def test_get_iso_timestamp_from_time_string(ts, expected_iso):
    iso_ts = utils.get_iso_timestamp(ts)

    assert iso_ts == expected_iso


def test_iso_timestamp_fails_for_unknown_format():
    with pytest.raises(ValueError):
        utils.get_iso_timestamp("19-05-2025 14:25:01")


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
