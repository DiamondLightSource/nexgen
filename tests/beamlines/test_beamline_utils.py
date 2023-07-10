from nexgen.beamlines.beamline_utils import BeamlineAxes, PumpProbe
from nexgen.nxs_utils import Axis, TransformationType
from nexgen.utils import Point3D
from tests.beamlines.conftest import axes_list as gonio_axes


def test_pump_probe():
    pump_probe = PumpProbe()
    pump_probe.pump_status = True
    pump_probe.pump_exposure = 0.01
    assert pump_probe.pump_status is True
    assert pump_probe.pump_exposure == 0.01
    assert pump_probe.pump_delay is None


def test_pump_probe_dict():
    pump_probe = PumpProbe().to_dict()
    assert list(pump_probe.keys()) == [
        "pump_status",
        "pump_exposure",
        "pump_delay",
        "pump_repeat",
    ]
    assert pump_probe["pump_status"] is False


def test_pump_status_set_to_true_if_exposure_is_passed():
    pump_probe = PumpProbe(pump_exposure=0.1)
    assert pump_probe.pump_status is True


def test_beamline_axes():
    bl = BeamlineAxes(
        gonio=gonio_axes,
        det_axes=[Axis("det_z", ".", TransformationType.TRANSLATION, (0, 0, 1))],
        fast_axis=(0, 1, 0),
        slow_axis=(1, 0, 0),
    )
    assert isinstance(bl.fast_axis, Point3D) is True
    assert isinstance(bl.slow_axis, Point3D) is True
