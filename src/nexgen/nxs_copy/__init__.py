"""
Utilities for copying metadata to new NeXus files.
"""

import h5py

from typing import List

from ..nxs_write import create_attributes


def get_nexus_tree(
    nxs_in: h5py.File,
    nxs_out: h5py.File,
    skip: bool = True,
    skip_obj: List[str] = ["data"],
):
    """
    Copy the tree from the original NeXus file. Everything except NXdata is copied to a new NeXus file.
    If skip is False, then the full tree is copied.

    Args:
        nxs_in:     Original NeXus file.
        nxs_out:    New NeXus file.
        skip:       Defaults to True, copy everything but NXdata.
                    Pass False to copy the whole NXentry tree.
        skip_obj:   List of objects not to be copied.
                    For now, it can only skip NX_class objects.
    Returns:
        nxentry:    NeXus field.
    """
    if skip is True:
        nxentry = nxs_out.create_group("entry")
        create_attributes(nxentry, ("NX_class",), ("NXentry",))
        # Copy all of the nexus tree as it is except for the group passed as skip_obj
        for k in nxs_in["entry"].keys():
            if k in skip_obj:
                continue
            nxs_in["entry"].copy(k, nxentry)
        return nxentry
    else:
        # Then copy everything
        nxs_in.copy("entry", nxs_out)
        return


def identify_tristan_scan_axis(nxs_in: h5py.File):
    """
    Identify the scan_axis in the NeXus tree of a Tristan collection.

    Args:
        nxs_in:     Tristan NeXus file
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


def convert_scan_axis(nxsample: h5py.Group, nxdata: h5py.Group, ax: str):
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
