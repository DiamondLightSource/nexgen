"""
Utilities for copying metadata to new NeXus files.
"""

import h5py

# import numpy as np

# from .. import create_attributes


def get_nexus_tree(nxs_in: h5py.File, nxs_out: h5py.File, skip=True):
    """
    Copy the tree from the original NeXus file, except for NXdata.

    Args:
        nxs_in: original NeXus file.
        nxs_out:new NeXus file.
        skip:   default True, copy everything but NXdata.
                Pass False to copy also NXdata.
    """
    pass
