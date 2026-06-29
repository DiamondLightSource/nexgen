"""
Define beamline parameter constants for I19-2 goniometer, Tristan and Eiger detectors.
"""

from nexgen.beamlines.beamline_utils import BeamlineAxes
from nexgen.nxs_utils import Axis, TransformationType
from nexgen.utils import Point3D

DEFAULT_DATA_KEY = "data"

I19_2_GONIO = [
    Axis("omega", ".", TransformationType.ROTATION, Point3D(-1, 0, 0)),
    Axis(
        "kappa", "omega", TransformationType.ROTATION, Point3D(-0.642788, -0.766044, 0)
    ),
    Axis("phi", "kappa", TransformationType.ROTATION, Point3D(-1, 0, 0)),
    Axis("sam_z", "phi", TransformationType.TRANSLATION, Point3D(0, 0, 1)),
    Axis("sam_y", "sam_z", TransformationType.TRANSLATION, Point3D(0, 1, 0)),
    Axis("sam_x", "sam_y", TransformationType.TRANSLATION, Point3D(1, 0, 0)),
]

I19_2_EIGER = BeamlineAxes(
    gonio=I19_2_GONIO,
    det_axes=[
        Axis("two_theta", ".", TransformationType.ROTATION, Point3D(-1, 0, 0)),
        Axis("det_z", "two_theta", TransformationType.TRANSLATION, Point3D(0, 0, 1)),
    ],
    fast_axis=Point3D(0, 1, 0),
    slow_axis=Point3D(-1, 0, 0),
)

I19_2T_TRISTAN = BeamlineAxes(
    gonio=I19_2_GONIO,
    det_axes=[
        Axis("two_theta", ".", TransformationType.ROTATION, Point3D(-1, 0, 0), 0),
        Axis("det_z", "two_theta", TransformationType.TRANSLATION, Point3D(0, 0, 1)),
    ],
    fast_axis=Point3D(-1, 0, 0),
    slow_axis=Point3D(0, 1, 0),
)
