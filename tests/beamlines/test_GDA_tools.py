from nexgen.beamlines.GDAtools.ExtendedRequest import (
    ExtendedRequestIO,
    read_det_position_from_xml,
    read_scan_from_xml,
)
from nexgen.beamlines.GDAtools.GDAjson2params import JSONParamsIO


def test_get_coordinate_frame_from_json(dummy_geometry_json):
    assert JSONParamsIO(dummy_geometry_json.name).get_coordinate_frame() == "mcstas"


def test_get_gonio_axes_from_json(dummy_geometry_json):
    gonio_axes = JSONParamsIO(dummy_geometry_json.name).get_goniometer_axes_from_file()
    assert isinstance(gonio_axes, list) and len(gonio_axes) == 3
    assert gonio_axes[0].name == "omega" and gonio_axes[1].name == "sam_x"
    assert gonio_axes[2].name == "phi" and gonio_axes[2].depends == "sam_x"


def test_get_detector_axes_from_json(dummy_geometry_json):
    det_axes = JSONParamsIO(dummy_geometry_json.name).get_detector_axes_from_file()
    assert isinstance(det_axes, list) and len(det_axes) == 1
    assert det_axes[0].name == "det_z"


def test_get_fast_and_slow_dir_from_json(dummy_detector_json):
    fast, slow = JSONParamsIO(
        dummy_detector_json.name
    ).get_fast_and_slow_direction_vectors_from_file("eiger")
    assert (fast.x, fast.y, fast.z) == (0, 1, 0)
    assert (slow.x, slow.y, slow.z) == (-1, 0, 0)


def test_get_detector_params_from_json(dummy_detector_json):
    params = JSONParamsIO(dummy_detector_json.name).get_detector_params_from_file()
    assert params.description == "Eiger 2X"
    assert params.image_size == [2162, 2068]
    assert params.pixel_size == ["7.5e-05m", "7.5e-05m"]


def test_ExtendedRequestIO(dummy_xml_file):
    test_ecr = ExtendedRequestIO(dummy_xml_file.name)
    assert test_ecr.getAxisChoice() == "omega"
    assert test_ecr.getCollectionInfo() == ("/path/to/data", "Filename", "1")
    assert test_ecr.getTransmission() == 10.0
    assert test_ecr.getResolution() == 1.0


def test_read_scan_from_xml(dummy_xml_file):
    test_ecr = ExtendedRequestIO(dummy_xml_file.name)
    scan_axis, pos, num = read_scan_from_xml(test_ecr)
    assert scan_axis == test_ecr.getAxisChoice()
    assert num == 10
    assert isinstance(pos, dict) and len(pos) == 6  # gonio axes on I19-2
    assert pos["omega"] == (-180.0, -160.0, 2)
    assert pos["phi"] == (*2 * (test_ecr.getOtherAxis(),), 0.0)


def test_read_det_position_from_xml(dummy_xml_file):
    test_ecr = ExtendedRequestIO(dummy_xml_file.name)
    det_pos = read_det_position_from_xml(test_ecr, "Eiger")
    assert det_pos[0] == test_ecr.getTwoTheta()
    assert det_pos[1] == test_ecr.getSampleDetectorDistance()
