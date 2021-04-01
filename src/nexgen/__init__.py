"""
Utilities for creating NeXus format files.
"""

__author__ = "Diamond Light Source - Scientific Software"
__email__ = "scientificsoftware@diamond.ac.uk"
__version__ = "0.4.0"
__version_tuple__ = tuple(int(x) for x in __version__.split("."))

import numpy as np

# from h5py import AttributeManager


def imgcif2mcstas(vector):
    """
    Convert from the standard coordinate frame used by imgCIF/CBF to the
    NeXus McStas coordinate system.

    Args:
        vector: array of coordinates
    Returns:
        Tuple with the converted coordinate values
    """
    c2n = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]])
    return tuple(np.dot(c2n, vector))
