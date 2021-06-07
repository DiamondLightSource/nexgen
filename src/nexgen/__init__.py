"""
General tools useful to create NeXus format files.
"""

__author__ = "Diamond Light Source - Scientific Software"
__email__ = "scientificsoftware@diamond.ac.uk"
__version__ = "0.5.0"
__version_tuple__ = tuple(int(x) for x in __version__.split("."))

import sys
import numpy as np

from h5py import AttributeManager
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


def create_attributes(nxs_obj, names, values):
    """
    Create or overwrite attributes with additional metadata information.

    Args:
        nxs_obj: NeXus object (Group or Dataset) to which the attributes should be attached
        names: Tuple containing the names of the new attributes
        values: Tuple containing the values relative to the names
    """
    for n, v in zip(names, values):
        if type(v) is str:
            # If a string, convert to numpy.string_
            v = np.string_(v)
        AttributeManager.create(nxs_obj, name=n, data=v)


def set_dependency(dep_info, path=None):
    """
    Define value for "depends_on" attribute.
    If the attribute points to the head of the dependency chain, simply pass "." for dep_info.

    Args:
        dep_info: The name of the transformation upon which the current one depends on.
        path: Where the transformation is. Set to None, if passed it points to location in the NeXus tree.
    Returns:
        The value to be passed to the attribute "depends_on"
    """
    if dep_info == ".":
        return np.string_(".")
    #    _d = dep_info
    #    if _d == ".":
    #        return numpy.string_(_d)
    #    else:
    #        _s = path + _d
    #        return numpy.string_(_s)

    if path:
        return np.string_(path + dep_info)
    else:
        return np.string_(dep_info)


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
