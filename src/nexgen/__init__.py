"""
General tools useful to create NeXus format files.
"""
from __future__ import annotations

__author__ = "Diamond Light Source - Scientific Software"
__email__ = "data_analysis@diamond.ac.uk"
__version__ = "0.6.21"
__version_tuple__ = tuple(int(x) for x in __version__.split("."))

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import h5py
import numpy as np
from numpy.typing import ArrayLike

# Logging set up
logging.getLogger("nexgen").addHandler(logging.NullHandler())

# Define scope extract type
# Scope = freephil.common.scope_extract

# Filename pattern: filename_######.h5 or filename_meta.h5
# P = re.compile(r"(.*)_(?:\d+)")
P = re.compile(r"(.*)_(?:meta|\d+)")


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
