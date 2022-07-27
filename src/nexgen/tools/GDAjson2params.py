"""
Tools to extract goniometer and detector parameters from GDA JSON files.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple


def read_geometry_from_json(
    axes_geometry: Path | str,
) -> Tuple[Dict, Dict]:
    """
    A function to read the axes information from the GDA-supplied json file.

    Args:
        axes_geometry (Union[Path, str]): JSON file containing the description of the axes and their location.

    Returns:
        Tuple[Dict, Dict]: Returns the updated dictionaries describing goniometer and detector.
    """
    goniometer = {}
    detector = {}

    # Load information from JSON file
    with open(axes_geometry) as f:
        geom = json.load(f)

    coordinate_frame = geom["geometry"]
    print(coordinate_frame)

    # Set up the dictionaries (in theory they are empty even when passed)
    goniometer["axes"] = []
    goniometer["depends"] = []
    goniometer["vectors"] = []
    goniometer["units"] = []
    goniometer["types"] = []

    detector["axes"] = []
    detector["depends"] = []
    detector["vectors"] = []
    detector["units"] = []
    detector["types"] = []

    for v in geom.values():
        if type(v) is dict:
            if v["location"] == "sample":
                goniometer["axes"].append(v["ds_name"])
                goniometer["depends"].append(
                    v["depends_on"].split("_")[1]
                    if "_" in v["depends_on"]
                    else v["depends_on"]
                )
                goniometer["types"].append(v["type"])
                goniometer["units"].append(v["units"])
                [goniometer["vectors"].append(i) for i in v["vector"]]
            elif v["location"] == "detector":
                detector["axes"].append(v["ds_name"])
                detector["depends"].append(v["depends_on"])
                detector["types"].append(v["type"])
                detector["units"].append(v["units"])
                [detector["vectors"].append(i) for i in v["vector"]]

    for j in range(len(goniometer["depends"])):
        if goniometer["depends"][j] in ["x", "y", "z"]:
            goniometer["depends"][j] = "sam_" + goniometer["depends"][j]
    goniometer["offsets"] = len(goniometer["axes"]) * [0, 0, 0]

    return goniometer, detector


def read_detector_params_from_json(
    detector_params: Path | str,
) -> Dict:
    """
    A function to read the detector parameters from the GDA-supplied json file.

    Args:
        detector_params (Union[Path, str]):  JSON file containing the definition of detector parameters.

    Returns:
        Dict: Updated detector dictionary
    """
    detector = {}

    # Load information from JSON file
    with open(detector_params) as f:
        det = json.load(f)

    if "tristan" in det.keys():
        detector["mode"] = "events"
        detector["description"] = det["tristan"]["description"]
        detector["image_size"] = det["tristan"]["data_size_sf"][::-1]
        detector["detector_type"] = det["tristan"]["detector_type"]
        detector["sensor_material"] = (
            "Si"
            if det["tristan"]["sensor_material"] == "Silicon"
            else det["tristan"]["sensor_material"]
        )
        detector["sensor_thickness"] = (
            str(det["tristan"]["sensor_thickness"])
            + det["tristan"]["sensor_thickness_units"]
        )
        detector["pixel_size"] = [
            str(i) + det["tristan"]["pixel_size_units"]
            for i in det["tristan"]["pixel_size_sf"][::-1]
        ]
        detector["fast_axis"] = det["tristan"]["fast_dir"]
        detector["slow_axis"] = det["tristan"]["slow_dir"]
        detector["flatfield_applied"] = False
        detector["pixel_mask_applied"] = False
        # ... and the tristan specifics
        spec = det["detector_specific"]
        detector["software_version"] = spec["software_version"]
        detector["detector_tick"] = (
            str(spec["detector_tick"]) + spec["detector_tick_units"]
        )
        detector["detector_frequency"] = (
            str(spec["detector_frequency"]) + spec["detector_frequency_units"]
        )
        detector["timeslice_rollover"] = spec["timeslice_rollover_bits"]
    elif "eiger" in det.keys():
        detector["mode"] = "images"
        detector["description"] = det["eiger"]["description"]
        detector["detector_type"] = det["eiger"]["type"]
        detector["image_size"] = det["eiger"]["size"]
        detector["sensor_material"] = det["eiger"]["sensor_material"]
        detector["sensor_thickness"] = (
            str(det["eiger"]["thickness"]) + det["eiger"]["thickness_units"]
        )
        detector["pixel_size"] = [
            str(i) + det["eiger"]["pixel_Size_units"]
            for i in det["eiger"]["pixel_size"]
        ]
        detector["fast_axis"] = det["eiger"]["fast_dir"]
        detector["slow_axis"] = det["eiger"]["slow_dir"]
    else:
        print("which detector is this then?")

    return detector
