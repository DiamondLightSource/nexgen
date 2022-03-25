"""
Tools to extract goniometer and detector parameters from GDA JSON files.
"""
import json

from typing import Dict, Tuple, Union
from pathlib import Path


def read_geometry_from_json(
    axes_geometry: Union[Path, str], goniometer: Dict = {}, detector: Dict = {}
) -> Tuple[Dict, Dict]:
    """
    A function to read the axes information from the GDA-supplied json file.

    Args:
        axes_geometry (Union[Path, str]): Description of the axes and their location.
        goniometer (Dict, optional): _description_. Defaults to {}.
        detector (Dict, optional): _description_. Defaults to {}.

    Returns:
        Tuple[Dict, Dict]: Returns the updated dictionaries describing goniometer and detector.
    """
    # Load information from JSON file
    with open(axes_geometry, "r") as f:
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
    detector_params: Union[Path, str],
    detector: Dict = {},
) -> Dict:
    """
    A function to read the detector parameters from the GDA-supplied json file.

    Args:
        detector_params (Union[Path, str]): Definition of detector parameters.
        detector (Dict, optional): _description_. Defaults to {}.

    Returns:
        Dict: Updated detector dictionary
    """
    # Load information from JSON file
    with open(detector_params, "r") as f:
        det = json.load(f)
    print(det)

    if "tristan" in det.keys():
        print("tristan")
    elif "eiger" in det.keys():
        print("eiger")
    else:
        print("which detector is this then?")
