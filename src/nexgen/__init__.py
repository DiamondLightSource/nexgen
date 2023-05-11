"""
General tools useful to create NeXus format files.
"""
from __future__ import annotations

__author__ = "Diamond Light Source - Scientific Software"
__email__ = "data_analysis@diamond.ac.uk"
__version__ = "0.6.24"
__version_tuple__ = tuple(int(x) for x in __version__.split("."))

import logging
from typing import Any, Dict, List, Tuple

import numpy as np
from numpy.typing import ArrayLike

MAX_FRAMES_PER_DATASET = 1000
MAX_SUFFIX_DIGITS = 6

# Logging set up
logging.getLogger("nexgen").addHandler(logging.NullHandler())


def imgcif2mcstas(vector: List | Tuple | ArrayLike) -> Tuple:
    """
    Convert from the standard coordinate frame used by imgCIF/CBF to the
    NeXus McStas coordinate system.

    Args:
        vector (List | Tuple | np.array): Coordinates to be converted.

    Returns:
        Tuple: Converted coordinate values.
    """
    c2n = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]])
    return tuple(np.dot(c2n, vector))


def coord2mcstas(vector: List | Tuple | ArrayLike, mat: ArrayLike) -> Tuple:
    """
    General conversion from a new coordinate convention to the NeXus McStas coordinate system.

    Args:
        vector (List | Tuple | np.array): Coordinates to be converted.
        mat (np.ndarray): Coordinate transformation matrix.

    Returns:
        Tuple: Converted coordinate values
    """
    return tuple(np.dot(mat, vector))


def split_arrays(axes_names: List, array: List) -> Dict[str, Tuple]:
    """Split a list of values into arrays.

    This function splits up the list of values passed as input (eg. phil parameters, dictionary) \
    for vector, offset for all existing axes.

    Args:
        axes_names (List): Axes names.
        array (List): Array of values to be split up. It must be

    Raises:
        ValueError: When each axes doesn't have a corresponding array of size 3.

    Returns:
        array_dict (Dict[str, Tuple]): Dictionary of arrays corresponding to each axis. Keys are axes names.
    """
    array_dict = {}
    if len(axes_names) == len(array):
        array_dict = {ax: tuple(v) for ax, v in zip(axes_names, array)}
        return array_dict
    elif len(array) == 3 * len(axes_names):
        for j in range(len(axes_names)):
            a = array[3 * j : 3 * j + 3]
            array_dict[axes_names[j]] = tuple(a)
        return array_dict
    else:
        raise ValueError(
            f"Number of axes {len(axes_names)} doesn't match the lenght of the array list {len(array)}."
            "Please check again and make sure that all axes have a matching array of size 3."
        )


def reframe_arrays(
    goniometer: Dict[str, Any],
    detector: Dict[str, Any],
    module: Dict[str, Any],
    coordinate_frame: str = "mcstas",
    new_coord_system: Dict[str, Any] = None,
):
    """
    Split a list of offset/vector values into arrays. If the coordinate frame is not mcstas, \
    convert the arrays using the base vectors of the new coordinate system.

    Args:
        goniometer (Dict[str, Any]): Goniometer geometry description.
        detector (Dict[str, Any]): Detector specific parameters and its axes.
        module (Dict[str, Any]): Geometry and description of detector module.
        coordinate_frame (str, optional): Coordinate system being used. If "imgcif", there's no need to pass a \
            new coordinate system definition, as the conversion is already included in nexgen. Defaults to "mcstas".
        new_coord_system (Dict[str, Any], optional): Definition of the current coordinate system. \
            It should at least contain a string defining the convention, origin and axes information as a tuple of (depends_on, type, units, vector). \
            e.g. for X axis: {"x": (".", "translation", "mm", [1,0,0])}. \
            Defaults to None.

    Raises:
        ValueError: When the input coordinate system name and the coordinate system convention for the vectors doesn't match.
    """
    # If the arrays of vectors/offsets are not yet split, start by doing that
    goniometer["vectors"] = list(
        split_arrays(goniometer["axes"], goniometer["vectors"]).values()
    )
    goniometer["offsets"] = list(
        split_arrays(goniometer["axes"], goniometer["offsets"]).values()
    )

    detector["vectors"] = list(
        split_arrays(detector["axes"], detector["vectors"]).values()
    )

    if "offsets" in module.keys():
        module["offsets"] = list(
            split_arrays(["fast_axis", "slow_axis"], module["offsets"]).values()
        )

    # Now proceed with conversion if needed
    if coordinate_frame.lower() != "mcstas":
        if coordinate_frame.lower() == "imgcif":
            # Goniometer
            goniometer["vectors"] = [imgcif2mcstas(v) for v in goniometer["vectors"]]
            goniometer["offsets"] = [imgcif2mcstas(v) for v in goniometer["offsets"]]

            # Detector
            detector["vectors"] = [imgcif2mcstas(v) for v in detector["vectors"]]

            # Module
            module["fast_axis"] = imgcif2mcstas(module["fast_axis"])
            module["slow_axis"] = imgcif2mcstas(module["slow_axis"])
            if "offsets" in module.keys():
                module["offsets"] = [imgcif2mcstas(off) for off in module["offsets"]]
        else:
            if coordinate_frame != new_coord_system["convention"]:
                raise ValueError(
                    "The input coordinate frame value doesn't match the current cordinate system convention."
                    "Impossible to convert to mcstas."
                )
            mat = np.array(
                [
                    new_coord_system["x"][-1],
                    new_coord_system["y"][-1],
                    new_coord_system["z"][-1],
                ]
            )

            # Goniometer
            goniometer["vectors"] = [
                coord2mcstas(v, mat) for v in goniometer["vectors"]
            ]
            goniometer["offsets"] = [
                coord2mcstas(v, mat) for v in goniometer["offsets"]
            ]

            # Detector
            detector["vectors"] = [coord2mcstas(v, mat) for v in detector["vectors"]]

            # Module
            module["fast_axis"] = coord2mcstas(module["fast_axis"], mat)
            module["slow_axis"] = coord2mcstas(module["slow_axis"], mat)
            if "offsets" in module.keys():
                module["offsets"] = [
                    coord2mcstas(off, mat) for off in module["offsets"]
                ]
