"""
Define parameters for Electron Diffraction with Singla detector.
"""

from ..nxs_utils import Axis, TransformationType
from ..utils import Point3D
from .beamline_utils import BeamlineAxes

EDSingla = BeamlineAxes(
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
    # "x": (".", "translation", "mm", [0, 1, 0]),  # (depends, type, unit, vector)
    # "y": ("x", "translation", "mm", [-1, 0, 0]),
    # "z": ("y", "translation", "mm", [0, 0, 1]),
}

goniometer = {
    "axes": ["alpha", "sam_z", "sam_y", "sam_x"],
    "depends": [".", "alpha", "sam_z", "sam_y"],
    "vectors": [(-1, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0)],
    "types": ["rotation", "translation", "translation", "translation"],
    "units": ["deg", "mm", "mm", "mm"],
    "offsets": [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)],
    "starts": None,
    "ends": None,
    "increments": None,
}

singla_1M = {
    "mode": "images",
    "description": "Dectris Singla 1M",
    "detector_type": "HPC",
    "sensor_material": "Si",
    "sensor_thickness": "0.450mm",
    "overload": 199996,
    "underload": -1,
    "pixel_size": ["0.075mm", "0.075mm"],
    "beam_center": None,
    "flatfield": None,
    "pixel_mask": None,
    "exposure_time": None,
    "image_size": [1062, 1028],  # (slow, fast)
    "axes": ["det_z"],
    "depends": ["."],
    "vectors": [0, 0, 1],
    "types": ["translation"],
    "units": ["mm"],
    "starts": None,
    "ends": None,
    "increments": 0.0,
}

module = {
    "fast_axis": [-1, 0, 0],
    "slow_axis": [0, -1, 0],
    "module_offset": "1",
}

source = {
    "name": "Diamond Light Source",
    "short_name": "DLS",
    "type": "Electron Source",
    "beamline_name": "eBIC",
    "probe": "electron",
}

beam = {
    "wavelength": 0.02,
    "flux": None,
}
