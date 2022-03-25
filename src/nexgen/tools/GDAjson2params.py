"""
Tools to extract goniometer and detector parameters from GDA JSON files.
"""
import json

from typing import Dict, Union
from pathlib import Path


def read_geometry_from_json(
    axes_geometry: Union[Path, str], goniometer: Dict = {}
) -> Dict:
    """_summary_

    Args:
        axes_geometry (Union[Path, str]): _description_
        goniometer (Dict, optional): _description_. Defaults to {}.

    Returns:
        Dict: _description_
    """
    # Load information from JSON file
    with open(axes_geometry, "r") as f:
        geom = json.load(f)
    print(geom)


def read_detector_params_from_json(
    detector_params: Union[Path, str],
    detector: Dict = {},
    goniometer: Dict = {},
) -> Dict:
    """_summary_

    Args:
        detector_params (Union[Path, str]): _description_
        detector (Dict, optional): _description_. Defaults to {}.
        goniometer (Dict, optional): _description_. Defaults to {}.

    Returns:
        Dict: _description_
    """
    # Load information from JSON file
    with open(detector_params, "r") as f:
        det = json.load(f)
    print(det)
