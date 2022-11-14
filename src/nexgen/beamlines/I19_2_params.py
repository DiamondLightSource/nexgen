"""
Define beamline parameters for I19-2, Tristan and Eiger detectors.
"""
source = {
    "name": "Diamond Light Source",
    "short_name": "DLS",
    "type": "Synchrotron X-ray Source",
    "beamline_name": "I19-2",
}

goniometer_axes = {
    "axes": ["omega", "kappa", "phi", "sam_z", "sam_y", "sam_x"],
    "depends": [".", "omega", "kappa", "phi", "sam_z", "sam_y"],
    "vectors": [
        (-1, 0, 0),
        (-0.642788, -0.766044, 0),
        (-1, 0, 0),
        (0, 0, -1),
        (0, -1, 0),
        (-1, 0, 0),
    ],
    "types": [
        "rotation",
        "rotation",
        "rotation",
        "translation",
        "translation",
        "translation",
    ],
    "units": ["deg", "deg", "deg", "mm", "mm", "mm"],
    "offsets": [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)],
    "starts": None,
    "ends": None,
    "increments": None,
}

tristan10M_params = {
    "mode": "events",
    "description": "Tristan 10M",
    "detector_type": "Pixel",
    "sensor_material": "Si",
    "sensor_thickness": "0.0005m",
    "pixel_size": ["5.5e-05m", "5.5e-05m"],
    "flatfield": "Tristan10M_flat_field_coeff_with_Mo_17.479keV.h5",
    "flatfield_applied": False,
    "pixel_mask": "Tristan10M_mask_with_spec.h5",
    "pixel_mask_applied": False,
    "image_size": [3043, 4183],  # (slow, fast)
    "axes": ["two_theta", "det_z"],
    "depends": [".", "two_theta"],
    "vectors": [(-1, 0, 0), (0, 0, 1)],
    "types": ["rotation", "translation"],
    "units": ["deg", "mm"],
    "starts": None,
    "ends": None,
    "increments": [0.0, 0.0],
    "software_version": "1.1.3",
    "fast_axis": [-1, 0, 0],
    "slow_axis": [0, 1, 0],
    "detector_tick": "1562.5ps",
    "detector_frequency": "6.4e+08Hz",
    "timeslice_rollover": 18,
}

eiger4M_params = {
    "mode": "images",
    "description": "Eiger 2X 4M",
    "detector_type": "Pixel",
    "sensor_material": "CdTe",
    "sensor_thickness": "0.750mm",
    "overload": 50649,  # "_dectris/countrate_correction_count_cutoff",
    "underload": -1,
    "pixel_size": ["0.075mm", "0.075mm"],
    "flatfield": "flatfield",
    "flatfield_applied": "_dectris/flatfield_correction_applied",
    "pixel_mask": "mask",
    "pixel_mask_applied": "_dectris/pixel_mask_applied",
    "image_size": [2162, 2068],  # (slow, fast)
    "axes": ["two_theta", "det_z"],
    "depends": [".", "two_theta"],
    "vectors": [(-1, 0, 0), (0, 0, 1)],
    "types": ["rotation", "translation"],
    "units": ["deg", "mm"],
    "starts": None,
    "ends": None,
    "increments": [0.0, 0.0],
    "bit_depth_readout": "_dectris/bit_depth_readout",
    "detector_readout_time": "_dectris/detector_readout_time",
    "threshold_energy": "_dectris/threshold_energy",
    "software_version": "_dectris/software_version",
    "serial_number": "_dectris/detector_number",
    "fast_axis": [0, 1, 0],
    "slow_axis": [-1, 0, 0],
}

dset_links = [
    [
        "pixel_mask",
        "pixel_mask_applied",
        "flatfield",
        "flatfield_applied",
        "threshold_energy",
        "bit_depth_readout",
        "detector_readout_time",
        "serial_number",
    ],
    ["software_version"],
]
