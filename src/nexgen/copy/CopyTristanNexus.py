"""
Tools for copying the metadata from Tristan NeXus files.
"""

import os
import h5py
import numpy as np

# from pathlib import Path

from . import get_nexus_tree, identify_scan_axis, convert_scan_axis
from .. import create_attributes


def single_image_nexus(data_file, tristan_nexus, write_mode="x"):
    """
    Create a NeXus file for a single-image data set.

    Copy the nexus tree from the original NeXus file for a collection on Tristan
    detector. In this case the input scan_axis is a tuple with the same start and
    stop value. The scan_axis in the new file will therefore be one single value.

    Args:
        data_file:      HDF5 file containing the newly binned images.
        tristan_nexus:  NeXus file with experiment metadata to be copied.
        write_mode:     Mode for writing the output NeXus file.  Accepts any valid
                        h5py file opening mode.

    Returns:
        The name of the output NeXus file.
    """
    nxs_filename = os.path.splitext(data_file)[0] + ".nxs"
    with h5py.File(tristan_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, write_mode
    ) as nxs_out:
        # Copy the whole tree except for nxdata
        nxentry = get_nexus_tree(nxs_in, nxs_out)
        # Create nxdata group
        nxdata = nxentry.create_group("data")
        # Add link to data
        nxdata["data"] = h5py.ExternalLink(data_file, "data")
        # Compute and write axis information
        ax, ax_attr = identify_scan_axis(nxs_in)
        create_attributes(
            nxdata, ("NX_class", "axes", "signal"), ("NXdata", ax, "data")
        )
        try:
            ax_range = nxs_in["entry/data"][ax][0]
        except ValueError:
            # Some early Tristan data from before March 2021, where the goniometer
            # was not moved during the data collection, record the rotation axis
            # position as a scalar.
            ax_range = nxs_in["entry/data"][ax][()]
        nxdata.create_dataset(ax, data=ax_range)
        # Write the attributes
        for key, value in ax_attr:
            nxdata[ax].attrs.create(key, value)
        # Now fix all other instances of scan_axis in the tree
        nxsample = nxentry["sample"]
        convert_scan_axis(nxsample, nxdata, ax)

    return nxs_filename


def multiple_images_nexus(
    data_file, tristan_nexus, write_mode="x", osc=None, nbins=None
):
    """
    Create a NeXus file for a multiple-image data set.

    Copy the nexus tree from the original NeXus file for a collection on Tristan
    detector. In this case multiple images from a rotation collection have been
    binned. Thus the scan_axis in the input file is a tuple (start, stop). The
    scan_axis in the new file will therefore be a list of angles. ang_vel and
    num_bins are mutually exclusive arguments to work out the scan_axis list.

    Args:
        data_file:      HDF5 file containing the newly binned images.
        tristan_nexus:  NeXus file with experiment metadata to be copied.
        write_mode:     Mode for writing the output NeXus file.  Accepts any valid
                        h5py file opening mode.
        osc:            Oscillation angle (degrees).
        nbins:          Number of binned images.

    Returns:
        The name of the output NeXus file.
    """
    nxs_filename = os.path.splitext(data_file)[0] + ".nxs"
    with h5py.File(tristan_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, write_mode
    ) as nxs_out:
        # Copy the whole tree except for nxdata
        nxentry = get_nexus_tree(nxs_in, nxs_out)
        # Create nxdata group
        nxdata = nxentry.create_group("data")
        # Add link to data
        nxdata["data"] = h5py.ExternalLink(data_file, "data")
        # Compute and write axis information
        ax, ax_attr = identify_scan_axis(nxs_in)
        create_attributes(
            nxdata, ("NX_class", "axes", "signal"), ("NXdata", ax, "data")
        )
        try:
            (start, stop) = nxs_in["entry/data"][ax][()]
        except (TypeError, ValueError):
            # Some early Tristan data from before March 2021, where the goniometer
            # was not moved during the data collection, record the rotation axis
            # position as a scalar.
            start = stop = nxs_in["entry/data"][ax][()]

        if osc and nbins:
            raise ValueError(
                "osc and nbins are mutually exclusive, " "please pass only one of them."
            )
        elif osc:
            ax_range = np.arange(start, stop, osc)
        elif nbins:
            ax_range = np.linspace(start, stop, nbins + 1)[:-1]
        else:
            raise ValueError(
                "Impossible to calculate scan_axis, " "please pass either osc or nbins."
            )

        nxdata.create_dataset(ax, data=ax_range)
        # Write the attributes
        for key, value in ax_attr:
            nxdata[ax].attrs.create(key, value)
        # Now fix all other instances of scan_axis in the tree
        nxsample = nxentry["sample"]
        convert_scan_axis(nxsample, nxdata, ax)

    return nxs_filename


def pump_probe_nexus(data_file, tristan_nexus, write_mode="x", mode="static"):
    """
    Create a NeXus file for a pump-probe image data set.

    Copy the nexus tree from the original NeXus file for a collection on Tristan
    detector. In this case multiple images from a pump-probe experiment have been
    binned. Thus the scan_axis in the input file is a tuple (start, stop). The
    scan_axis in the new file will be a single value if chosen mode is not
    "rotation". TBD rotation + pump-probe

    Args:
        data_file:      HDF5 file containing the newly binned images.
        tristan_nexus:  NeXus file with experiment metadata to be copied.
        write_mode:     Mode for writing the output NeXus file.  Accepts any valid
                        h5py file opening mode.
        mode:           "static", "powder_diffraction" or "rotation"

    Returns:
        The name of the output NeXus file.
    """
    # TODO: figure out a better way
    assert mode in ["static", "powder_diffraction", "rotation"], (
        "Mode passed is not valid, please pass one of the following "
        "['static', 'powder_diffraction', 'rotation']"
    )

    nxs_filename = os.path.splitext(data_file)[0] + ".nxs"
    with h5py.File(tristan_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, write_mode
    ) as nxs_out:
        # Copy the whole tree except for nxdata
        nxentry = get_nexus_tree(nxs_in, nxs_out)
        # Create nxdata group
        nxdata = nxentry.create_group("data")
        # Add link to data
        nxdata["data"] = h5py.ExternalLink(data_file, "data")
        # Compute and write axis information
        ax, ax_attr = identify_scan_axis(nxs_in)
        create_attributes(
            nxdata, ("NX_class", "axes", "signal"), ("NXdata", ax, "data")
        )
        if mode in ["static", "powder_diffraction"]:
            try:
                ax_range = nxs_in["entry/data"][ax][0]
            except ValueError:
                # Some early Tristan data from before March 2021, where the goniometer
                # was not moved during the data collection, record the rotation axis
                # position as a scalar.
                ax_range = nxs_in["entry/data"][ax][()]
        # else:
        # TODO
        nxdata.create_dataset(ax, data=ax_range)
        # Write the attributes
        for key, value in ax_attr:
            nxdata[ax].attrs.create(key, value)
        # Now fix all other instances of scan_axis in the tree
        nxsample = nxentry["sample"]
        convert_scan_axis(nxsample, nxdata, ax)

    return nxs_filename
