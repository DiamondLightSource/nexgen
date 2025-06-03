import pytest
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


@pytest.fixture
def det_axes() -> list[Axis]:
    return [
        Axis("two_theta", ".", TransformationType.ROTATION, Point3D(1, 0, 0), 0.0),
        Axis(
            "det_z",
            "two_theta",
            TransformationType.TRANSLATION,
            Point3D(0, 0, 1),
            500.0,
        ),
    ]


@pytest.fixture
def eiger() -> EigerDetector:
    return EigerDetector("Eiger2 1M", (1028, 1062), "Si", 10000, -1)


@pytest.fixture
def tristan() -> TristanDetector:
    return TristanDetector("Tristan 1M", (515, 2069))


@pytest.fixture
def jungfrau() -> JungfrauDetector:
    return JungfrauDetector("Jungfrau 1M", (1066, 1030))


@pytest.fixture
def singla() -> SinglaDetector:
    return SinglaDetector("Singla 1M", (1062, 1028))


def test_eiger_detector(eiger: EigerDetector):
    assert eiger.description == "Eiger2 1M"
    assert eiger.sensor_material == "Si"
    assert eiger.sensor_thickness == "0.450mm"
    assert eiger.pixel_size == ["0.075mm", "0.075mm"]
    assert eiger.hasMeta is True


def test_tristan_detector(tristan: TristanDetector):
    assert tristan.description == "Tristan 1M"
    assert tristan.sensor_material == "Si"
    assert tristan.sensor_thickness == "0.5mm"
    assert tristan.mode == "events"
    assert tristan.hasMeta is True


def test_jungfrau_detector(jungfrau: JungfrauDetector):
    assert jungfrau.description == "Jungfrau 1M"
    assert jungfrau.sensor_material == "Si"
    assert jungfrau.sensor_thickness == "0.320mm"
    assert jungfrau.hasMeta is False
    assert isinstance(jungfrau.constants, dict)


def test_singla_detector(singla: SinglaDetector):
    assert singla.description == "Singla 1M"
    assert singla.sensor_thickness == "0.450mm"
    assert singla.detector_type == "HPC"
    assert singla.hasMeta is False


def test_detector_axes(eiger: EigerDetector, det_axes: list[Axis]):
    det = Detector(eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)])
    assert isinstance(det.detector_axes, list)
    assert det.detector_axes[0].name == "two_theta"
    assert det.detector_axes[1].name == "det_z"
    assert [det.detector_axes[0].depends, det.detector_axes[1].depends] == [
        ".",
        "two_theta",
    ]


def test_get_detector_description(eiger: EigerDetector, det_axes: list[Axis]):
    eig = Detector(eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)])
    assert eig.get_detector_description() == eiger.description


def test_get_detector_mode_for_eiger(eiger: EigerDetector, det_axes: list[Axis]):
    eig = Detector(eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)])
    assert eig.get_detector_mode() == "images"


def test_get_detector_mode_for_tristan(tristan: TristanDetector, det_axes: list[Axis]):
    tr = Detector(tristan, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)])
    assert tr.get_detector_mode() == "events"


def test_detector_to_module_dict(eiger: EigerDetector, det_axes: list[Axis]):
    mod = Detector(
        eiger, det_axes, [100, 200], 0.1, [(0, 0, 1), Point3D(0, -1, 0)]
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
