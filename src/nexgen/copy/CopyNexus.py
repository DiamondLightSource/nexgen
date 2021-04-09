"""
General tools to copy metadata from NeXus files.
"""
import os
import h5py

from . import get_nexus_tree
from .. import create_attributes


def images_nexus(data_file, original_nexus, skip=True):
    """
    Copy NeXus metadata for images.

    Args:
        data_file:       HDF5 file.
        original_nexus:  NeXus file with experiment metadata.
        skip:            Default True. If False, copy everything
    """
    nxs_filename = os.path.splitext(data_file)[0] + ".nxs"
    with h5py.File(original_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, "x"
    ) as nxs_out:
        if skip is True:
            # Copy the whole tree except for nxdata
            nxentry = get_nexus_tree(nxs_in, nxs_out)
            # Create nxdata group
            nxdata = nxentry.create_group("data")
            # Find and copy only scan axis information
            for k in nxs_in["entry/data"].keys():
                if "depends_on" in nxs_in["entry/data"][k].attrs.keys():
                    ax = k
                    nxs_in["entry/data"].copy(k, nxdata)
            create_attributes(
                nxdata, ("NX_class", "axes", "signal"), ("NXdata", ax, "data")
            )
            # Add link to data
            with h5py.File(data_file, "r") as fout:
                nxdata["data"] = h5py.ExternalLink(fout.filename, "data")
        else:
            # Copy the whole tree including nxdata
            nxentry = get_nexus_tree(nxs_in, nxs_out, skip)


def pseudo_events_nexus(data_file, original_nexus):
    """
    Copy NeXus metadata for pseudo event mode data.

    Args:
        data_file:       HDF5 file.
        original_nexus:  NeXus file with experiment metadata.
    """
    nxs_filename = os.path.splitext(data_file)[0] + ".nxs"
    with h5py.File(original_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, "x"
    ) as nxs_out:
        # Copy the whole tree except for nxdata
        nxentry = get_nexus_tree(nxs_in, nxs_out)
        # Create nxdata group
        nxdata = nxentry.create_group("data")
        # Find and copy only scan axis information
        for k in nxs_in["entry/data"].keys():
            if "depends_on" in nxs_in["entry/data"][k].attrs.keys():
                ax = k
                nxs_in["entry/data"].copy(k, nxdata)
        create_attributes(
            nxdata, ("NX_class", "axes", "signal"), ("NXdata", ax, "data")
        )
        # Add link to data
        with h5py.File(data_file, "r") as fout:
            for k in fout.keys():
                nxdata[k] = h5py.ExternalLink(fout.filename, k)
