import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_utils import Axis, Detector, EigerDetector, TristanDetector
from nexgen.nxs_utils.Detector import UnknownDetectorTypeError
from nexgen.utils import Point3D

det_axes = [
    Axis("two_theta", ".", "rotation", Point3D(1, 0, 0), 0.0),
    Axis("det_z", "two_theta", "translation", Point3D(0, 0, 1), 500.0),
]

test_eiger = EigerDetector("Eiger2 1M", (1028, 1062), "Si", 10000, -1)
test_tristan = TristanDetector("Tristan 1M", (515, 2069))


def test_eiger_detector():
    assert test_eiger.description == "Eiger2 1M"
    assert test_eiger.sensor_material == "Si"
    assert test_eiger.sensor_thickness == "0.450mm"
    assert test_eiger.pixel_size == ["0.075mm", "0.075mm"]


def test_tristan_detector():
    assert test_tristan.description == "Tristan 1M"
    assert test_tristan.sensor_material == "Si"
    assert test_tristan.sensor_thickness == "0.5mm"
    assert test_tristan.mode == "events"


def test_detector_axes():
    det = Detector(
        test_eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    )
    assert type(det.detector_axes) is list
    assert det.detector_axes[0].name == "two_theta"
    assert det.detector_axes[1].name == "det_z"
    assert [det.detector_axes[0].depends, det.detector_axes[1].depends] == [
        ".",
        "two_theta",
    ]


def test_detector_to_dict_raises_error_if_unknown_type():
    with pytest.raises(UnknownDetectorTypeError):
        Detector(
            "", det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
        ).to_dict()


def test_get_detector_description():
    eig = Detector(
        test_eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    )
    assert eig.get_detector_description() == test_eiger.description


def test_eiger_detector_to_dict():
    eig = Detector(
        test_eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    ).to_dict()
    assert "pixel_mask" in list(eig.keys())
    assert "threshold_energy" in list(eig.keys())


def tristan_detector_to_dict():
    trist = Detector(
        test_tristan, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    ).to_dict()
    assert "timeslice_rollover" in list(trist.keys())


def test_detector_to_module_dict():
    mod = Detector(
        test_eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    ).to_module_dict()
    assert type(mod) is dict
    assert mod["module_offset"] == "1"
    assert_array_equal(mod["fast_axis"], [0, 0, 1])
    assert_array_equal(mod["slow_axis"], [0, -1, 0])


def test_fast_slow_axis_input():
    det = Detector(
        test_eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    )
    assert type(det.fast_axis) is Point3D and type(det.slow_axis) is Point3D
    assert det.fast_axis == Point3D(0, 0, 1)
