"""
Define parameters for Electron Diffraction with Singla detector.
"""

from ..nxs_utils import Axis, Facility, Source, TransformationType
from ..utils import Point3D
from .beamline_utils import BeamlineAxes

EDSingla = BeamlineAxes(
    gonio=[
        Axis("alpha", ".", TransformationType.ROTATION, Point3D(0, -1, 0)),
        Axis("sam_z", "alpha", TransformationType.TRANSLATION, Point3D(0, 0, 1)),
        Axis("sam_y", "sam_z", TransformationType.TRANSLATION, Point3D(0, 1, 0)),
        Axis("sam_x", "sam_y", TransformationType.TRANSLATION, Point3D(1, 0, 0)),
    ],
    det_axes=[Axis("det_z", ".", TransformationType.TRANSLATION, Point3D(0, 0, 1))],
    fast_axis=Point3D(-1, 0, 0),
    slow_axis=Point3D(0, -1, 0),
)


EDCeta = BeamlineAxes(
    gonio=[
        Axis("alpha", ".", TransformationType.ROTATION, Point3D(-1, 0, 0)),
        Axis("sam_z", "alpha", TransformationType.TRANSLATION, Point3D(0, 0, 1)),
        Axis("sam_y", "sam_z", TransformationType.TRANSLATION, Point3D(0, 1, 0)),
        Axis("sam_x", "sam_y", TransformationType.TRANSLATION, Point3D(1, 0, 0)),
    ],
    det_axes=[Axis("det_z", ".", TransformationType.TRANSLATION, Point3D(0, 0, 1))],
    fast_axis=Point3D(-1, 0, 0),
    slow_axis=Point3D(0, -1, 0),
)


coordinate_frame = "mcstas"

ED_coord_system = {
    "convention": "ED",
    "origin": (0, 0, 0),
    "x": Axis("x", ".", TransformationType.TRANSLATION, Point3D(0, 1, 0)),
    "y": Axis("y", "x", TransformationType.TRANSLATION, Point3D(-1, 0, 0)),
    "z": Axis("z", "y", TransformationType.TRANSLATION, Point3D(0, 0, 1)),
}

EDSource = Source(
    "eBIC",
    Facility("Diamond Light Source", "DLS", "Electron Source", "DIAMOND MICROSCOPE"),
    "electron",
)
