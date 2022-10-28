"""
Define parameters for Electron Diffraction
"""

coordinate_frame = "mcstas"

ED_coord_system = {
    "convention": "ED",
    "origin": (0, 0, 0),
    "x": (".", "translation", "mm", [0, 1, 0]),  # (depends, type, unit, vector)
    "y": ("x", "translation", "mm", [-1, 0, 0]),
    "z": ("y", "translation", "mm", [0, 0, 1]),
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
    "type": "Synchrotron X-ray Source",
    "beamline_name": "eBic",
    "probe": "electron",
}

beam = {
    "wavelength": 0.02,
    "flux": None,
}
