from nexgen.beamlines.beamline_utils import BeamlineAxes, PumpProbe
from nexgen.nxs_utils import Axis, TransformationType
from nexgen.utils import Point3D


def test_pump_probe():
    pump_probe = PumpProbe()
    pump_probe.pump_status = True
    pump_probe.pump_exposure = 0.01
    assert pump_probe.pump_status is True
    assert pump_probe.pump_exposure == 0.01
    assert pump_probe.pump_delay is None


def test_pump_probe_dict():
    pump_probe = PumpProbe().model_dump()
    assert list(pump_probe.keys()) == [
        "pump_status",
        "pump_exposure",
        "pump_delay",
        "pump_repeat",
    ]
    assert pump_probe["pump_status"] is False


def test_beamline_axes(i24_axes_list):
    bl = BeamlineAxes(
        gonio=i24_axes_list,
        det_axes=[Axis("det_z", ".", TransformationType.TRANSLATION, (0, 0, 1))],
        fast_axis=(0, 1, 0),
        slow_axis=(1, 0, 0),
    )
    assert isinstance(bl.fast_axis, Point3D) is True
    assert isinstance(bl.slow_axis, Point3D) is True
