"""
General tools useful to create NeXus format files.
"""

__author__ = "Diamond Light Source - Scientific Software"
__email__ = "scientificsoftware@diamond.ac.uk"
__version__ = "0.5.2"
__version_tuple__ = tuple(int(x) for x in __version__.split("."))

import sys
import numpy as np

from pathlib import Path


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


def get_filename_template(master_filename: Path) -> str:
    """
    Get the data file name template from the master file.

    Args:
        master_filename:    Path object containing the name of master file.
                            The format should be either file_master.h5 or file.nxs.
    Returns:
        filename_template:  String template for the name of blank data file.
    """
    if master_filename.suffix == ".nxs":
        filename_root = master_filename.stem
        filename_template = master_filename.parent / f"{filename_root}_%0{6}d.h5"
    elif master_filename.suffix == ".h5":
        filename = master_filename.stem.replace("master", f"%0{6}d")
        filename_template = master_filename.parent / f"{filename}.h5"
    else:
        sys.exit("Master file did not have the expected format.")
    # so that filename_template.as_posix() % 1 will become filename_000001.h5
    return filename_template.as_posix()


def split_arrays(coord_frame, axes_names, array):
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
    # array_list = []
    array_dict = {}
    for j in range(len(axes_names)):
        a = array[3 * j : 3 * j + 3]
        if coord_frame == "imgcif":
            # array_list.append(imgcif2mcstas(a))
            array_dict[axes_names[j]] = imgcif2mcstas(a)
        else:
            # array_list.append(tuple(a))
            array_dict[axes_names[j]] = tuple(a)
    return array_dict
