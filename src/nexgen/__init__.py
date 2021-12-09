"""
General tools useful to create NeXus format files.
"""

__author__ = "Diamond Light Source - Scientific Software"
__email__ = "scientificsoftware@diamond.ac.uk"
__version__ = "0.6.0"
__version_tuple__ = tuple(int(x) for x in __version__.split("."))

import re
import sys
import h5py
import pint

# import freephil

import numpy as np

from pathlib import Path
from datetime import datetime
from typing import Any, Optional, List, Union

# Initialize registry and a Quantity constructor
ureg = pint.UnitRegistry()
Q_ = ureg.Quantity

# Define scope extract type
# Scope = freephil.common.scope_extract

# Filename pattern: filename_######.h5 or filename_meta.h5
# P = re.compile(r"(.*)_(?:\d+)")
P = re.compile(r"(.*)_(?:meta|\d+)")

# Format strings for timestamps
format_list = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%a %b %d %Y %H:%M:%S"]


def imgcif2mcstas(vector):
    """
    Convert from the standard coordinate frame used by imgCIF/CBF to the
    NeXus McStas coordinate system.

    Args:
        vector: Array of coordinates
    Returns:
        Tuple with the converted coordinate values
    """
    c2n = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]])
    return tuple(np.dot(c2n, vector))


def get_filename_template(input_filename: Path) -> str:
    """
    Get the data file name template from either the master or the meta file.

    Args:
        master_filename:    Path object containing the name of master or meta file.
                            The format should be either file_master.h5, file.nxs for a master file,
                            file_meta.h5 for a meta file.
    Returns:
        filename_template:  String template for the name of blank data file.
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
        sys.exit(
            "Input file did not have the expected format for a master or meta file."
        )
    # so that filename_template.as_posix() % 1 will become filename_000001.h5
    return filename_template.as_posix()


def get_nexus_filename(input_filename: Path) -> Path:
    """
    Get the filename for the NeXus file from the stem of the input file name, by .

    Args:
        input_filename:  File name and path of either a .h5 data file or a _meta.h5 file.
    Returns:
        NeXus file name (.nxs) path.
    """
    filename_stem = P.fullmatch(input_filename.stem)[1]
    nxs_filename = input_filename.parent / f"{filename_stem}.nxs"
    return nxs_filename


def walk_nxs(nxs_obj: Union[h5py.File, h5py.Group]) -> List[str]:
    """
    Walk all the groups, subgroups and datasets of an object.

    Args:
        nxs_obj:    Object to walk through, could be a file or a group.
    Returns:
        obj_list:   List of strings.
    """
    obj_list = []
    nxs_obj.visit(obj_list.append)
    return obj_list


def split_arrays(coord_frame: str, axes_names: List, array: List) -> dict:
    """
    Split a list of values into arrays.

    This function splits up the list of values passed as phil parameters for vector, offset of all existing axes. If the coordinate frame is set to imgCIF, the arrays will have to be converted into mcstas.

    Args:
        coord_frame:    The coordinate system in which we are working: mcstas or imgCIF
        axes_names:     List of axes that have been passed as phil parameters
        array:          List of values to be split up
    Returns:
        array_dict:     Dictionary of arrays corresponding to each axis. Keys are axes names.
    """
    array_dict = {}
    for j in range(len(axes_names)):
        a = array[3 * j : 3 * j + 3]
        if coord_frame == "imgcif":
            array_dict[axes_names[j]] = imgcif2mcstas(a)
        else:
            array_dict[axes_names[j]] = tuple(a)
    return array_dict


def get_iso_timestamp(ts: str) -> str:
    """
    Format a timestamp string to be stores in a NeXus file according to ISO8601:
    'YY-MM-DDThh:mm:ssZ'

    Args:
        ts:     Input string, can also be a timestamp (eg. time.time()) string.
                Allowed formats: "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%a %b %d %Y %H:%M:%S".
    Returns:
        ts_iso: Output formatted string.
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
                pass
    if ts_iso.endswith("Z") is False:
        ts_iso += "Z"
    return ts_iso


def units_of_length(q: Any, to_base: Optional[bool] = False) -> Q_:  # -> pint.Quantity:
    """
    Check that a quantity of length is compatible with NX_LENGTH, defaulting to m if dimensionless.

    Args:
        q:          An object that can be interpreted as a pint Quantity, it can be dimensionless.
        to_base:    If True, convert to base units of length (m).
    Returns:
        quantity:   A pint quantity with units applied if it was dimensionless.
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
        q:          A string that can be interpreted as a pint Quantity, it can be dimensionless.
    Returns:
        quantity:   A pint quantity in s, with units applied if it was dimensionless.
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
