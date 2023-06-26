"""
Define and store basic beamline parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from nexgen.nxs_utils import Axis, TransformationType
from nexgen.utils import Point3D


@dataclass
class BeamlineAxes:
    """Beamline specific axes for goniometer, detector and detector module."""

    gonio: List[Axis]
    det_axes: List[Axis]
    fast_axis: Point3D
    slow_axis: Point3D


# I24
I24Eiger = BeamlineAxes(
    gonio=[
        Axis("omega", ".", TransformationType.ROTATION, (-1, 0, 0)),
        Axis("sam_z", "omega", TransformationType.TRANSLATION, (0, 0, 1)),
        Axis("sam_y", "sam_z", TransformationType.TRANSLATION, (0, 1, 0)),
        Axis("sam_x", "sam_y", TransformationType.TRANSLATION, (1, 0, 0)),
    ],
    det_axes=[Axis("det_z", ".", TransformationType.TRANSLATION, (0, 0, 1))],
    fast_axis=Point3D(-1, 0, 0),
    slow_axis=Point3D(0, -1, 0),
)

# I19-2
I19_2_gonio = [
    Axis("omega", ".", TransformationType.ROTATION, (-1, 0, 0)),
    Axis("kappa", "omega", TransformationType.ROTATION, (-0.642788, -0.766044, 0)),
    Axis("phi", "kappa", TransformationType.ROTATION, (-1, 0, 0)),
    Axis("sam_z", "phi", TransformationType.TRANSLATION, (0, 0, 1)),
    Axis("sam_y", "sam_z", TransformationType.TRANSLATION, (0, 1, 0)),
    Axis("sam_x", "sam_y", TransformationType.TRANSLATION, (1, 0, 0)),
]

I19_2Eiger = BeamlineAxes(
    gonio=I19_2_gonio,
    det_axes=[
        Axis("two_theta", ".", TransformationType.ROTATION, (-1, 0, 0)),
        Axis("det_z", "two_theta", TransformationType.TRANSLATION, (0, 0, 1)),
    ],
    fast_axis=Point3D(0, 1, 0),
    slow_axis=Point3D(-1, 0, 0),
)

I19_2Tristan = BeamlineAxes(
    gonio=I19_2_gonio,
    det_axes=[
        Axis("two_theta", ".", TransformationType.ROTATION, (-1, 0, 0), 0),
        Axis("det_z", "two_theta", TransformationType.TRANSLATION, (0, 0, 1)),
    ],
    fast_axis=Point3D(-1, 0, 0),
    slow_axis=Point3D(0, 1, 0),
)
