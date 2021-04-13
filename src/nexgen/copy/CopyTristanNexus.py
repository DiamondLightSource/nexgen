"""
Tools for copying the metadata from Tristan NeXus files.
"""

import os
import h5py
import numpy as np

# from pathlib import Path

from . import get_nexus_tree, identify_scan_axis, convert_scan_axis
from .. import create_attributes


def single_image_nexus(data_file, tristan_nexus):
    """
    Copy the nexus tree from the original NeXus file for a collection on Tristan detector.
    In this case the input scan_axis is a tuple with the same start and stop value.
    The scan_axis in the new file will therefore be one single value.

    Args:
        data_file:      HDF5 file containing the newly binned images.
        tristan_nexus:  NeXus file with experiment metadata to be copied.
    """
    nxs_filename = os.path.splitext(data_file)[0] + ".nxs"
    with h5py.File(tristan_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, "x"
    ) as nxs_out:
        # Copy the whole tree except for nxdata
        nxentry = get_nexus_tree(nxs_in, nxs_out)
        # Create nxdata group
        nxdata = nxentry.create_group("data")
        # Add link to data
        with h5py.File(data_file, "r") as fh:
            nxdata["data"] = h5py.ExternalLink(fh.filename, "data")
        # Compute and write axis information
        ax, ax_attr = identify_scan_axis(nxs_in)
        create_attributes(
            nxdata, ("NX_class", "axes", "signal"), ("NXdata", ax, "data")
        )
        ax_range = nxs_in["entry/data"][ax][0]
        nxdata.create_dataset(ax, data=ax_range)
        # Write the attributes
        for key, value in ax_attr:
            nxdata[ax].attrs.create(key, value)
        # Now fix all other instances of scan_axis in the tree
        nxsample = nxentry["sample"]
        convert_scan_axis(nxsample, nxdata, ax)


def multiple_images_nexus(data_file, tristan_nexus, ang_vel=None, nbins=None):
    """
    Copy the nexus tree from the original NeXus file for a collection on Tristan detector.
    In this case multiple images from a rotation collection have been binned.
    Thus the scan_axis in the input file is a tuple (start, stop).
    The scan_axis in the new file will therefore be a list of angles.
    ang_vel and num_bins are mutually exclusive arguments to work out the scan_axis list.

    Args:
        data_file:      HDF5 file containing the newly binned images.
        tristan_nexus:  NeXus file with experiment metadata to be copied.
        ang_vel:        Angular velocity, deg/s.
        nbins:       Number of binned images.
    """
    nxs_filename = os.path.splitext(data_file)[0] + ".nxs"
    with h5py.File(tristan_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, "x"
    ) as nxs_out:
        # Copy the whole tree except for nxdata
        nxentry = get_nexus_tree(nxs_in, nxs_out)
        # Create nxdata group
        nxdata = nxentry.create_group("data")
        # Add link to data
        with h5py.File(data_file, "r") as fh:
            nxdata["data"] = h5py.ExternalLink(fh.filename, "data")
        # Compute and write axis information
        ax, ax_attr = identify_scan_axis(nxs_in)
        create_attributes(
            nxdata, ("NX_class", "axes", "signal"), ("NXdata", ax, "data")
        )
        (start, stop) = nxs_in["entry/data"][ax][()]

        if ang_vel and nbins:
            raise ValueError(
                "ang_vel and nbins are mutually exclusive, please pass only one of them."
            )
        elif ang_vel:
            ax_range = np.array([round(p, 1) for p in np.arange(start, stop, ang_vel)])
        elif nbins:
            step = round(abs((stop - start) / nbins), 2)
            ax_range = np.array([round(p, 1) for p in np.arange(start, stop, step)])
        else:
            raise ValueError(
                "Impossible to calculate scan_axis, please pass either ang_vel or nbins."
            )

        nxdata.create_dataset(ax, data=ax_range)
        # Write the attributes
        for key, value in ax_attr:
            nxdata[ax].attrs.create(key, value)
        # Now fix all other instances of scan_axis in the tree
        nxsample = nxentry["sample"]
        convert_scan_axis(nxsample, nxdata, ax)


def pump_probe_nexus(data_file, tristan_nexus, mode="static"):
    """
    Copy the nexus tree from the original NeXus file for a collection on Tristan detector.
    In this case multiple images from a pump-probe experiment have been binned.
    Thus the scan_axis in the input file is a tuple (start, stop).
    The scan_axis in the new file will be a single value if chosen mode is not "rotation".
    TBD rotation + pump-probe

    Args:
        data_file:      HDF5 file containing the newly binned images.
        tristan_nexus:  NeXus file with experiment metadata to be copied.
        mode:           "static", "powder_diffraction" or "rotation"
    """
    # TODO: figure out a better way
    assert mode in [
        "static",
        "powder_diffraction",
        "rotation",
    ], "Mode passed is not valid, please pass one of the following ['static', 'powder_diffraction', 'rotation']"

    nxs_filename = os.path.splitext(data_file)[0] + ".nxs"
    with h5py.File(tristan_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, "x"
    ) as nxs_out:
        # Copy the whole tree except for nxdata
        nxentry = get_nexus_tree(nxs_in, nxs_out)
        # Create nxdata group
        nxdata = nxentry.create_group("data")
        # Add link to data
        with h5py.File(data_file, "r") as fh:
            nxdata["data"] = h5py.ExternalLink(fh.filename, "data")
        # Compute and write axis information
        ax, ax_attr = identify_scan_axis(nxs_in)
        create_attributes(
            nxdata, ("NX_class", "axes", "signal"), ("NXdata", ax, "data")
        )
        if mode in ["static", "powder_diffraction"]:
            ax_range = nxs_in["entry/data"][ax][0]
        # else:
        # TODO
        nxdata.create_dataset(ax, data=ax_range)
        # Write the attributes
        for key, value in ax_attr:
            nxdata[ax].attrs.create(key, value)
        # Now fix all other instances of scan_axis in the tree
        nxsample = nxentry["sample"]
        convert_scan_axis(nxsample, nxdata, ax)
