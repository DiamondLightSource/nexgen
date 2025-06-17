import math
from math import isclose

from nexgen.command_line.compare_pcap import (
    GridPlane,
    _load_nexus_data,
    _load_pcap_data,
)


def test_extract_xyzdata_from_master_file():
    actual_xyz_data = _load_nexus_data(
        "tests/test_data/xrc_209_master.h5", GridPlane.PLANE_XY
    )
    assert len(actual_xyz_data) == 240

    expected_x = [0.0694439, 0.0894439, 0.1094439, 0.1294439, 0.1494439]
    expected_y = [-0.3751945, -0.3751945, -0.3751945, -0.3751945, -0.3751945]
    expected_z = [-0.2191471, -0.2191471, -0.2191471, -0.2191471, -0.2191471]
    assert all(
        isclose(expected, actual.sam_x, abs_tol=1e-6)
        for expected, actual in zip(expected_x, actual_xyz_data[:5])
    )
    assert all(
        isclose(expected, actual.sam_y, abs_tol=1e-6)
        for expected, actual in zip(expected_y, actual_xyz_data[:5])
    )
    assert all(
        isclose(expected, actual.sam_z, abs_tol=1e-6)
        for expected, actual in zip(expected_z, actual_xyz_data[:5])
    )

    for xyz_data in actual_xyz_data:
        assert xyz_data.plane == GridPlane.PLANE_XY


def test_extract_pcap_data():
    actual_pcap_data = _load_pcap_data(
        "tests/test_data/panda.h5",
        ["INENC1.VAL.Mean", "INENC2.VAL.Mean", "INENC3.VAL.Mean"],
    )
    assert len(actual_pcap_data) == 870
    expected_x_data = [-math.nan, -0.6390871732, -0.6194395172, -0.5996009908]
    expected_y_data = [-math.nan, -0.14580513, -0.1461460604, -0.14598213]
    expected_z_data = [-math.nan, -0.116742654, -0.1167205656, -0.1166226884]
    assert all(
        isclose(expected, actual.sam_x, abs_tol=1e-6)
        for expected, actual in zip(expected_x_data[1:], actual_pcap_data[1:4])
    )
    assert all(
        isclose(expected, actual.sam_y, abs_tol=1e-6)
        for expected, actual in zip(expected_y_data[1:], actual_pcap_data[1:4])
    )
    assert all(
        isclose(expected, actual.sam_z, abs_tol=1e-6)
        for expected, actual in zip(expected_z_data[1:], actual_pcap_data[1:4])
    )
