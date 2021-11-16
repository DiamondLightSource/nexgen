"""
Define beamline parameters for I24 with Eiger 9M detector.
"""
source = {
    "name": "Diamond Light Source",
    "short_name": "DLS",
    "type": "Synchrotron X-ray Source",
    "beamline_name": "I24",
}

goniometer_axes = {
    "axes": ["omega", "sam_z", "sam_y", "sam_x"],
    "depends": [".", "omega", "sam_z", "sam_y"],
    "vectors": [-1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0],
    "types": ["rotation", "translation", "translation", "translation"],
    "units": ["deg", "mm", "mm", "mm"],
    "offsets": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
}

eiger9M_params = {
    "mode": "images",
    "description": "Eiger 2X 9M",
    "detector_type": "Pixel",
    "sensor_material": "CdTe",
    "sensor_thickness": "0.750mm",
    "overload": 1e07,
    "underload": -1,
    "pixel_size": ["0.075mm", "0.075mm"],
    "flatfield": None,
    "pixel_mask": None,
    "image_size": [3108, 3262],  # (fast, slow)
    "axes": ["det_z"],
    "depends": ["."],
    "vectors": [0, 0, 1],
    "types": ["translation"],
    "units": ["mm"],
    "fast_axis": [-1, 0, 0],
    "slow_axis": [0, -1, 0],
}
