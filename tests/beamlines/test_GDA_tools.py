from nexgen.beamlines.GDAtools.GDAjson2params import JSONParamsIO

GEOMETRY_JSON = "tests/beamlines/test_geometry.json"
DETECTOR_JSON = "tests/beamlines/test_detector.json"


def test_get_coordinate_frame_from_json():
    assert JSONParamsIO(GEOMETRY_JSON).get_coordinate_frame() == "mcstas"


def test_get_gonio_axes_from_json():
    gonio_axes = JSONParamsIO(GEOMETRY_JSON).get_goniometer_axes_from_file()
    assert type(gonio_axes) is list and len(gonio_axes) == 2
    assert gonio_axes[0].name == "omega" and gonio_axes[1].name == "sam_x"


def test_get_detector_axes_from_json():
    det_axes = JSONParamsIO(GEOMETRY_JSON).get_detector_axes_from_file()
    assert type(det_axes) is list and len(det_axes) == 1
    assert det_axes[0].name == "det_z"


def test_get_fast_and_slow_dir_from_json():
    fast, slow = JSONParamsIO(
        DETECTOR_JSON
    ).get_fast_and_slow_direction_vectors_from_file("eiger")
    assert (fast.x, fast.y, fast.z) == (0, 1, 0)
    assert (slow.x, slow.y, slow.z) == (-1, 0, 0)


def test_get_detector_params_from_json():
    params = JSONParamsIO(DETECTOR_JSON).get_detector_params_from_file()
    assert params.description == "Eiger 2X"
    assert params.image_size == [2162, 2068]
    assert params.pixel_size == ["7.5e-05m", "7.5e-05m"]
