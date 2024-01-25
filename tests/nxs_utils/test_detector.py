# import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_utils import (
    Axis,
    Detector,
    DetectorModule,
    EigerDetector,
    JungfrauDetector,
    SinglaDetector,
    TransformationType,
    TristanDetector,
)
from nexgen.utils import Point3D

det_axes = [
    Axis("two_theta", ".", TransformationType.ROTATION, Point3D(1, 0, 0), 0.0),
    Axis("det_z", "two_theta", TransformationType.TRANSLATION, Point3D(0, 0, 1), 500.0),
]

test_eiger = EigerDetector("Eiger2 1M", (1028, 1062), "Si", 10000, -1)
test_tristan = TristanDetector("Tristan 1M", (515, 2069))
test_jungfrau = JungfrauDetector("Jungfrau 1M", (1066, 1030))
test_singla = SinglaDetector("Singla 1M", (1062, 1028))


def test_eiger_detector():
    assert test_eiger.description == "Eiger2 1M"
    assert test_eiger.sensor_material == "Si"
    assert test_eiger.sensor_thickness == "0.450mm"
    assert test_eiger.pixel_size == ["0.075mm", "0.075mm"]
    assert test_eiger.hasMeta is True


def test_tristan_detector():
    assert test_tristan.description == "Tristan 1M"
    assert test_tristan.sensor_material == "Si"
    assert test_tristan.sensor_thickness == "0.5mm"
    assert test_tristan.mode == "events"
    assert test_eiger.hasMeta is True


def test_jungfrau_detector():
    assert test_jungfrau.description == "Jungfrau 1M"
    assert test_jungfrau.sensor_material == "Si"
    assert test_jungfrau.sensor_thickness == "0.320mm"
    assert test_jungfrau.hasMeta is False
    assert isinstance(test_jungfrau.constants, dict)


def test_singla_detector():
    assert test_singla.description == "Singla 1M"
    assert test_singla.sensor_thickness == "0.450mm"
    assert test_singla.detector_type == "HPC"
    assert test_singla.hasMeta is False


def test_detector_axes():
    det = Detector(
        test_eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    )
    assert isinstance(det.detector_axes, list)
    assert det.detector_axes[0].name == "two_theta"
    assert det.detector_axes[1].name == "det_z"
    assert [det.detector_axes[0].depends, det.detector_axes[1].depends] == [
        ".",
        "two_theta",
    ]


def test_get_detector_description():
    eig = Detector(
        test_eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    )
    assert eig.get_detector_description() == test_eiger.description


def test_get_detector_mode():
    eig = Detector(
        test_eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    )
    assert eig.get_detector_mode() == "images"

    tr = Detector(
        test_tristan, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    )
    assert tr.get_detector_mode() == "events"


def test_detector_to_module_dict():
    mod = Detector(
        test_eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
    ).get_module_info()
    assert isinstance(mod, dict)
    assert mod["module_offset"] == "1"
    assert_array_equal(mod["fast_axis"], (0, 0, 1))
    assert_array_equal(mod["slow_axis"], (0, -1, 0))


def test_fast_slow_axis_input():
    mod = DetectorModule((0, 0, 1), Point3D(0, -1, 0))

    assert isinstance(mod.fast_axis, tuple) and isinstance(mod.slow_axis, tuple)
    assert mod.fast_axis == (0, 0, 1)
    assert mod.slow_axis == (0, -1, 0)
    assert mod.module_offset == "1"
