"""
Utilities for creating NeXus format files.
"""

__author__ = "Diamond Light Source - Scientific Software"
__email__ = "scientificsoftware@diamond.ac.uk"
__version__ = "0.4.9"
__version_tuple__ = tuple(int(x) for x in __version__.split("."))

import numpy as np

from h5py import AttributeManager


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
