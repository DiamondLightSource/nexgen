"""
General tools useful to create NeXus format files.
"""
from __future__ import annotations

__author__ = "Diamond Light Source - Scientific Software"
__email__ = "data_analysis@diamond.ac.uk"
__version__ = "0.6.28"
__version_tuple__ = tuple(int(x) for x in __version__.split("."))

from typing import Dict, List, Tuple

import numpy as np
from numpy.typing import ArrayLike

MAX_FRAMES_PER_DATASET = 1000
MAX_SUFFIX_DIGITS = 6


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
