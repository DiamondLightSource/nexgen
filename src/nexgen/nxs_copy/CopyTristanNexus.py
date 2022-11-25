"""
Tools for copying the metadata from Tristan NeXus files.
"""
from __future__ import annotations

import logging
from pathlib import Path

import h5py
import numpy as np

from ..nxs_write import create_attributes
from . import (
    compute_ssx_axes,
    convert_scan_axis,
    find_chipmap_in_tristan_nxs,
    get_nexus_tree,
    identify_tristan_scan_axis,
)

tristan_logger = logging.getLogger("nexgen.CopyTristanNeXus")


def single_image_nexus(
    data_file: Path | str,
    tristan_nexus: Path | str,
    write_mode: str = "x",
) -> str:
    """
    Create a NeXus file for a single-image or a stationary pump-probe dataset.

    Copy the nexus tree from the original NeXus file for a collection on Tristan
    detector. In the case of a single image, the input scan_axis is a (start, stop) tuple where start and
    stop have the same value, for a pump-probe experiment the values might differ for some older datasets.
    The scan_axis in the new file will therefore be one single number, equal to the "start".

    Args:
        data_file (Optional[Union[Path, str]]): String or Path pointing to the HDF5 file containing the newly binned images.
        tristan_nexus (Optional[Union[Path, str]]): String or Path pointing to the input NeXus file with experiment metadata to be copied.
        write_mode (str, optional): String indicating writing mode for the output NeXus file.  Accepts any valid
                        h5py file opening mode. Defaults to "x".

    Returns:
        nxs_filename (str): The name of the output NeXus file.
    """
    data_file = Path(data_file).expanduser().resolve()
    tristan_nexus = Path(tristan_nexus).expanduser().resolve()
    nxs_filename = data_file.parent / f"{data_file.stem}.nxs"
    with h5py.File(tristan_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, write_mode
    ) as nxs_out:
        # Copy the whole tree except for nxdata
        nxentry = get_nexus_tree(nxs_in, nxs_out)
        # Create nxdata group
        nxdata = nxentry.create_group("data")
        # Add link to data
        nxdata["data"] = h5py.ExternalLink(data_file.name, "data")
        # Compute and write axis information
        ax, ax_attr = identify_tristan_scan_axis(nxs_in)
        if ax:
            create_attributes(
                nxdata,
                ("NX_class", "axes", "signal", ax + "_indices"),
                (
                    "NXdata",
                    ax,
                    "data",
                    [
                        0,
                    ],
                ),
            )
            try:
                ax_range = nxs_in["entry/data"][ax][0]
            except ValueError:
                # Some early Tristan data from before March 2021, where the goniometer
                # was not moved during the data collection, record the rotation axis
                # position as a scalar.
                ax_range = nxs_in["entry/data"][ax][()]
            nxdata.create_dataset(ax, data=np.array([ax_range]))
            # Write the attributes
            for key, value in ax_attr.items():
                nxdata[ax].attrs.create(key, value)
            # Now fix all other instances of scan_axis in the tree
            nxsample = nxentry["sample"]
            convert_scan_axis(nxsample, nxdata, ax)

    return nxs_filename.as_posix()


def multiple_images_nexus(
    data_file: Path | str,
    tristan_nexus: Path | str,
    write_mode: str = "x",
    osc: float = None,
    nbins: int = None,
) -> str:
    """
    Create a NeXus file for a multiple-image dataset or multiple image sequences from a pump-probe collection.

    Copy the nexus tree from the original NeXus file for a collection on Tristan detector. There are two main applications for this function.
    In the first case, multiple images from a rotation collection have been binned and the scan_axis to be found in the input file is a (start, stop) tuple.
    The scan_axis in the new file will therefore be a list of angles. Osc and num_bins are mutually exclusive arguments to work out the scan_axis list.
    In the second case, multiple images from a 2D grid scan collection have been binned. The "rotation" scan_axis is still to be found in the input file as a
    (start, stop) tuple - although in this instance the two values should coincide. The values for the "translation" scan axes instead can be worked out from
    the chipmap dictionary, saved as a Unicode string inside the original NeXus file during collection, and nbins. It should be noted that passing osc in this
    case will raise an error and exit.

    Args:
        data_file (Optional[Union[Path, str]]): String or Path pointing to the HDF5 file containing the newly binned images.
        tristan_nexus (Optional[Union[Path, str]]): String or Path pointing to the input NeXus file with experiment metadata to be copied.
        write_mode (str, optional): String indicating writing mode for the output NeXus file.  Accepts any valid
                        h5py file opening mode. Defaults to "x".
        osc (float, optional): Oscillation angle (degrees). Defaults to None.
        nbins (int, optional): Number of binned images. Defaults to None.

    Raises:
        ValueError: When osc has been passed instead of nbins for a grid scan collection.
        ValueError: When both osc and nbins have been passed for a rotation collection. The two values are mutually exclusive.
        ValueError: When neither osc nor nbins has been passed. It won't be possible to calculate the scan range without at least one of them.

    Returns:
        nxs_filename (str): The name of the output NeXus file.
    """
    data_file = Path(data_file).expanduser().resolve()
    tristan_nexus = Path(tristan_nexus).expanduser().resolve()
    nxs_filename = data_file.parent / f"{data_file.stem}.nxs"
    with h5py.File(tristan_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, write_mode
    ) as nxs_out:
        # Copy the whole tree except for nxdata
        nxentry = get_nexus_tree(nxs_in, nxs_out)
        # Create nxdata group
        nxdata = nxentry.create_group("data")
        # Add link to data
        nxdata["data"] = h5py.ExternalLink(data_file.name, "data")
        # Compute and write axis information
        ax, ax_attr = identify_tristan_scan_axis(nxs_in)
        if ax:
            create_attributes(
                nxdata,
                ("NX_class", "axes", "signal", ax + "_indices"),
                (
                    "NXdata",
                    ax,
                    "data",
                    [
                        0,
                    ],
                ),
            )
            try:
                (start, stop) = nxs_in["entry/data"][ax][()]
            except (TypeError, ValueError):
                # Some early Tristan data from before March 2021, where the goniometer
                # was not moved during the data collection, record the rotation axis
                # position as a scalar.
                start = stop = nxs_in["entry/data"][ax][()]

            # Write position based on whether it's a rotation scan or a grid scan
            if find_chipmap_in_tristan_nxs(nxs_in) is True:
                if osc and not nbins:
                    raise ValueError(
                        "For a grid scan please pass the number of binned images nbins instead of the oscillation."
                        "The scan axes translations can't be calculated from the oscillation angle."
                    )

                rot_ax, transl_ax, windows_per_bin = compute_ssx_axes(
                    nxs_in, nbins, ax, (start, stop)
                )  # Hopefully start and stop are the same
                nxsample = nxentry["sample"]

                # First rotation (attributes already found)
                nxdata.create_dataset(ax, data=rot_ax[ax])
                for key, value in ax_attr.items():
                    nxdata[ax].attrs.create(key, value)
                convert_scan_axis(nxsample, nxdata, ax)

                # Check whether multiple windows have been binned together
                if windows_per_bin is not None:
                    from ..nxs_write.NXclassWriters import write_NXnote

                    write_NXnote(
                        nxs_out, "/entry/data", {"windows_per_image": windows_per_bin}
                    )
                    # And exit here
                    return nxs_filename.as_posix()

                # Then translation axes
                for ax_name, ax_range in transl_ax.items():
                    nxdata.create_dataset(ax_name, data=ax_range)
                    # Get attributes for relevant axis in nxs_in
                    ax_attr = dict(
                        nxs_in["/entry/sample/transformations/" + ax_name].attrs
                    )
                    for key, value in ax_attr.items():
                        nxdata[ax_name].attrs.create(key, value)
                    convert_scan_axis(nxsample, nxdata, ax_name)
            else:
                if osc and nbins:
                    raise ValueError(
                        "osc and nbins are mutually exclusive, "
                        "please pass only one of them."
                    )
                elif osc:
                    ax_range = np.arange(start, stop, osc)
                elif nbins:
                    ax_range = np.linspace(start, stop, nbins + 1)[:-1]
                else:
                    raise ValueError(
                        "Impossible to calculate scan_axis, "
                        "please pass either osc or nbins."
                    )

                nxdata.create_dataset(ax, data=ax_range)
                # Write the attributes
                for key, value in ax_attr.items():
                    nxdata[ax].attrs.create(key, value)
                # Now fix all other instances of scan_axis in the tree
                nxsample = nxentry["sample"]
                convert_scan_axis(nxsample, nxdata, ax)

    return nxs_filename.as_posix()
