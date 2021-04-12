"""
Utilities for copying metadata to new NeXus files.
"""

import h5py

from .. import create_attributes


def get_nexus_tree(nxs_in: h5py.File, nxs_out: h5py.File, skip=True):
    """
    Copy the tree from the original NeXus file, except for NXdata.

    Args:
        nxs_in: original NeXus file.
        nxs_out:new NeXus file.
        skip:   default True, copy everything but NXdata.
                Pass False to copy also NXdata.
    Returns:
        nxentry field
        nothing is skip is False
    """
    if skip is True:
        nxentry = nxs_out.create_group("entry")
        create_attributes(nxentry, ("NX_class",), ("NXentry",))
        # Copy all of the nexus tree as it is except for /entry/data
        for k in nxs_in["entry"].keys():
            if k == "data":
                continue
            nxs_in["entry"].copy(k, nxentry)
        return nxentry
    else:
        # Then copy everything, even data
        nxs_in.copy("entry", nxs_out)
        return


def identify_scan_axis(nxs_in: h5py.File):
    """
    Identify the scan_axis in the NeXus tree.

    Args:
        nxs_in: Tristan NeXus file
    Returns:
        ax:         Name of the scan_axis
        ax_attrs:   Attributes of the scan_axis dataset, type h5py._hl.base.ItemsViewHDF5
    """
    nxdata = nxs_in["entry/data"]
    for k in nxdata.keys():
        try:
            if type(nxdata[k]) is h5py.Dataset:
                # in Tristan NeXus files everything else is a group
                ax = k
                ax_attr = nxdata[k].attrs.items()
        except KeyError:
            continue
    return ax, ax_attr


def convert_scan_axis(nxsample, nxdata, ax):
    """
    Modify all instances of scan_axis present in NeXus file NXsample group.

    Args:
        nxsample:   NXsample group of NeXus file to be modified
        nxdata:     NXdata group of NeXus file to be modified
        ax:         Name of scan_axis
    """
    del nxsample["transformations/" + ax]
    nxsample["transformations/" + ax] = nxdata[ax]
    name = "sample_" + ax + "/" + ax
    del nxsample[name]
    nxsample[name] = nxdata[ax]
