"""
Tools to extract goniometer and detector parameters from GDA JSON files.
"""

from typing import Union
from pathlib import Path


def read_geometry_from_json(axes_geometry: Union[Path, str]):
    """_summary_

    Args:
        axes_geometry (Union[Path, str]): _description_
    """
    #     # Load information from JSON file
    #     with open(axes_geometry, "r") as f:
    #         geom = json.load(f)
    #     print(geom)
    pass


def read_detector_params_from_json(
    detector_params: Union[Path, str],
):
    """_summary_

    Args:
        detector_params (Union[Path, str]): _description_
    """
    pass
