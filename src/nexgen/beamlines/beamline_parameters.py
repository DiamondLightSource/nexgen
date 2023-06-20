"""
Define and store basic beamline parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from nexgen.nxs_utils import Axis
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
        Axis("omega", ".", "rotation", (-1, 0, 0)),
        Axis("sam_z", "omega", "translation", (0, 0, 1)),
        Axis("sam_y", "sam_z", "translation", (0, 1, 0)),
        Axis("sam_x", "sam_y", "translation", (1, 0, 0)),
    ],
    det_axes=[Axis("det_z", ".", "translation", (0, 0, 1))],
    fast_axis=Point3D(-1, 0, 0),
    slow_axis=Point3D(0, -1, 0),
)

# I19-2
I19_2_gonio = [
    Axis("omega", ".", "rotation", (-1, 0, 0)),
    Axis("kappa", "omega", "rotation", (-0.642788, -0.766044, 0)),
    Axis("phi", "kappa", "rotation", (-1, 0, 0)),
    Axis("sam_z", "phi", "translation", (0, 0, 1)),
    Axis("sam_y", "sam_z", "translation", (0, 1, 0)),
    Axis("sam_x", "sam_y", "translation", (1, 0, 0)),
]

I19_2Eiger = BeamlineAxes(
    gonio=I19_2_gonio,
    det_axes=[
        Axis("two_theta", ".", "rotation", (-1, 0, 0)),
        Axis("det_z", "two_theta", "translation", (0, 0, 1)),
    ],
    fast_axis=Point3D(0, 1, 0),
    slow_axis=Point3D(-1, 0, 0),
)

I19_2Tristan = BeamlineAxes(
    gonio=I19_2_gonio,
    det_axes=[
        Axis("two_theta", ".", "rotation", (-1, 0, 0), 0),
        Axis("det_z", "two_theta", "translation", (0, 0, 1)),
    ],
    fast_axis=Point3D(-1, 0, 0),
    slow_axis=Point3D(0, 1, 0),
)
