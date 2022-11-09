"""
General tools useful to create NeXus format files.
"""
from __future__ import annotations

__author__ = "Diamond Light Source - Scientific Software"
__email__ = "scientificsoftware@diamond.ac.uk"
__version__ = "0.6.12"
__version_tuple__ = tuple(int(x) for x in __version__.split("."))

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import h5py
import numpy as np
import pint
from numpy.typing import ArrayLike

# Logging set up
logging.getLogger("nexgen").addHandler(logging.NullHandler())

# Initialize registry and a Quantity constructor
ureg = pint.UnitRegistry()
Q_ = ureg.Quantity

# Define scope extract type
# Scope = freephil.common.scope_extract

# Filename pattern: filename_######.h5 or filename_meta.h5
# P = re.compile(r"(.*)_(?:\d+)")
P = re.compile(r"(.*)_(?:meta|\d+)")

# Format strings for timestamps
format_list = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%a %b %d %Y %H:%M:%S",
    "%A, %d. %B %Y %I:%M%p",
]


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


def coord2mcstas(vector: List | Tuple | np.array, mat: ArrayLike) -> Tuple:
    """
    General conversion from a new coordinate convention to the NeXus McStas coordinate system.

    Args:
        vector (List | Tuple | np.array): Coordinates to be converted.
        mat (np.ndarray): Coordinate transformation matrix.

    Returns:
        Tuple: Converted coordinate values
    """
    return tuple(np.dot(mat, vector))


def get_filename_template(input_filename: Path) -> str:
    """
    Get the data file name template from either the master or the meta file.

    Args:
        input_filename (Path): Path object containing the name of master or meta file.
                            The format should be either file_master.h5, file.nxs for a master file, file_meta.h5 for a meta file.

    Raises:
        NameError: If the input file does not have the expected format.

    Returns:
        filename_template (str): String template for the name of blank data file.
    """
    if input_filename.suffix == ".nxs":
        filename_root = input_filename.stem
        filename_template = input_filename.parent / f"{filename_root}_%0{6}d.h5"
    elif input_filename.suffix == ".h5" and "master" in input_filename.as_posix():
        filename = input_filename.stem.replace("master", f"%0{6}d")
        filename_template = input_filename.parent / f"{filename}.h5"
    elif input_filename.suffix == ".h5" and "meta" in input_filename.as_posix():
        filename = input_filename.stem.replace("meta", f"%0{6}d")
        filename_template = input_filename.parent / f"{filename}.h5"
    else:
        raise NameError(
            "Input file did not have the expected format for a master or meta file."
        )
    # so that filename_template.as_posix() % 1 will become filename_000001.h5
    return filename_template.as_posix()


def get_nexus_filename(input_filename: Path, copy: bool = False) -> Path:
    """
    Get the filename for the NeXus file from the stem of the input file name.

    Args:
        input_filename (Path): File name and path of either a .h5 data file or a _meta.h5 file.
        copy (bool, optional): Avoid trying to write a new file with the same name as the old one when making a copy. Defaults to False.

    Returns:
        Path: NeXus file name (.nxs) path.
    """
    filename_stem = P.fullmatch(input_filename.stem)
    if filename_stem:
        filename = filename_stem[1]
    else:
        filename = input_filename.stem

    if copy is True:
        nxs_filename = input_filename.parent / f"{filename}_copy.nxs"
    else:
        nxs_filename = input_filename.parent / f"{filename}.nxs"
    return nxs_filename


def walk_nxs(nxs_obj: h5py.File | h5py.Group) -> List[str]:
    """
    Walk all the groups, subgroups and datasets of an object.

    Args:
        nxs_obj (h5py.File | h5py.Group): Object to walk through, could be a file or a group.

    Returns:
        obj_list (List[str]): List of objects found, as strings.
    """
    obj_list = []
    nxs_obj.visit(obj_list.append)
    return obj_list


def split_arrays(
    coord_frame: str, axes_names: List, array: List, mat: ArrayLike = None
) -> Dict[str, Tuple]:
    """
    Split a list of values into arrays.

    This function splits up the list of values passed as phil parameters for vector, offset of all existing axes.
    If the coordinate frame is set to imgCIF, or to any other system different from mcstas, the arrays will have to be converted.
    While the conversion from imgCIF is predefined inside nexgen, for any other coordinate frame it is necessary to give the relative \
    transformation matrix.

    Args:
        coord_frame (str): The coordinate system in which we are working: mcstas or imgCIF.
        axes_names (List): List of goniometer axes.
        array (List): List of vector values to be split up.
        mat (np.ndarray, optional): Coordinate transformation matrix.

    Returns:
        array_dict (Dict[str, Tuple]): Dictionary of arrays corresponding to each axis. Keys are axes names.
    """
    array_dict = {}
    for j in range(len(axes_names)):
        a = array[3 * j : 3 * j + 3]
        if coord_frame == "imgcif":
            array_dict[axes_names[j]] = imgcif2mcstas(a)
        elif coord_frame != "mcstas" and coord_frame != "imgcif":
            array_dict[axes_names[j]] = coord2mcstas(a, mat)
        else:
            array_dict[axes_names[j]] = tuple(a)
    return array_dict


def get_iso_timestamp(ts: str | float) -> str:
    """
    Format a timestamp string to be stores in a NeXus file according to ISO8601: 'YY-MM-DDThh:mm:ssZ'

    Args:
        ts (str | float): Input string, can also be a timestamp (eg. time.time()) string.
                        Allowed formats: "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%a %b %d %Y %H:%M:%S", "%A, %d. %B %Y %I:%M%p".

    Returns:
        ts_iso (str): Formatted timestamp.
    """
    if ts is None:
        return None
    try:
        ts = float(ts)
        ts_iso = datetime.utcfromtimestamp(ts).replace(microsecond=0).isoformat()
    except ValueError:
        for fmt in format_list:
            try:
                ts_iso = datetime.strptime(ts, fmt).isoformat()
            except ValueError:
                ts_iso = str(ts)
    if ts_iso.endswith("Z") is False:
        ts_iso += "Z"
    return ts_iso


def units_of_length(q: Any, to_base: bool = False) -> Q_:  # -> pint.Quantity:
    """
    Check that a quantity of length is compatible with NX_LENGTH, defaulting to m if dimensionless.

    Args:
        q (Any): An object that can be interpreted as a pint Quantity, it can be dimensionless.
        to_base (bool, optional): If True, convert to base units of length (m). Defaults to False.

    Raises:
        ValueError: If the input value is a negative number.
        pint.errors.DimensionalityError: If the input value is not a quantity of lenght.

    Returns:
        quantity (pint.Quantity): A pint quantity with units applied if it was dimensionless.
    """
    quantity = Q_(q)
    if quantity <= 0:
        raise ValueError("Quantity (length) must be positive.")
    quantity = quantity * ureg.m if quantity.dimensionless else quantity
    if quantity.check("[length]"):
        if to_base is True:
            return quantity.to_base_units()
        else:
            return quantity
    else:
        raise pint.errors.DimensionalityError(
            quantity, "a quantity of", quantity.dimensionality, ureg.mm.dimensionality
        )


def units_of_time(q: str) -> Q_:  # -> pint.Quantity:
    """
    Check that a quantity of time is compatible with NX_TIME, defaulting to s if dimensionless.
    Convert to seconds if time is passed as a fraction of it.

    Args:
        q (str): A string that can be interpreted as a pint Quantity, it can be dimensionless.

    Raises:
        ValueError: If the input value is a negative number.
        pint.errors.DimensionalityError: If the input value is not a quantity of lenght.

    Returns:
        quantity (pint.Quantity): A pint quantity in s, with units applied if it was dimensionless.
    """
    quantity = Q_(q)
    if quantity <= 0:
        raise ValueError("Quantity (time) of time must be positive.")
    quantity = quantity * ureg.s if quantity.dimensionless else quantity
    if quantity.check("[time]"):
        return quantity.to_base_units()
    else:
        raise pint.errors.DimensionalityError(
            quantity, "a quantity of", quantity.dimensionality, ureg.s.dimensionality
        )
