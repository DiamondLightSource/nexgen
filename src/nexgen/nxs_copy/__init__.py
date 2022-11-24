"""
Utilities for copying metadata to new NeXus files.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import h5py
import numpy as np

from .. import walk_nxs
from ..beamlines.SSX_chip import Chip, compute_goniometer
from ..nxs_write import calculate_scan_range, create_attributes


def h5str(h5_value: str | np.string_ | bytes) -> str:
    """
    Convert a value returned an h5py attribute to str.

    h5py can return either a bytes-like (numpy.string_) or str object
    for attribute values depending on whether the value was written as
    fixed or variable length. This function collapses the two to str.

    Args:
        h5_value (str | np.string_ | bytes): Original attribute value.

    Returns:
        str: Attribute value collapsed to str.
    """
    if isinstance(h5_value, (np.string_, bytes)):
        return h5_value.decode("utf-8")
    return h5_value


def get_skip_list(nxentry: h5py.Group, skip_obj: List[str]) -> List[str]:
    """
    Get a list of all the objects that should not be copied in the new NeXus file.

    Args:
        nxentry (h5py.Group): NXentry group of a NeXus file.
        skip_obj (List[str]): List of objects that should not be copied.

    Returns:
        skip_list (List[str]): List of "NXclass" objects to skip during copy.
    """
    obj_list = walk_nxs(nxentry)
    skip_list = []
    for obj in obj_list:
        try:
            if nxentry[obj].attrs["NX_class"] in np.string_(skip_obj):
                skip_list.append(obj)
        except Exception:
            pass
    return skip_list


def get_nexus_tree(
    nxs_in: h5py.File,
    nxs_out: h5py.File,
    skip: bool = True,
    skip_obj: List[str] = None,
) -> h5py.Group | None:
    """
    Copy the tree from the original NeXus file. Everything except NXdata is copied to a new NeXus file.
    If skip is False, then the full tree is copied.

    Args:
        nxs_in (h5py.File): Original NeXus file.
        nxs_out (h5py.File): New NeXus file.
        skip (bool, optional): Copy everything but objects in skip_obj, which always include NXdata.
                            Pass False to copy the whole NXentry tree. Defaults to True.
        skip_obj (List[str], optional): List of NX_class objects not to be copied, eg. 'NXdata' or 'NXdetector'.. Defaults to None.

    Returns:
        h5py.Group | None: The group NXentry or nothing if the full file is copied.
    """
    skip_obj = ["NXdata"] if skip_obj is None else skip_obj

    if skip is True:
        nxentry = nxs_out.create_group("entry")
        create_attributes(nxentry, ("NX_class", "default"), ("NXentry", "data"))
        # Copy all of the nexus tree as it is except for the group passed as skip_obj
        skip_list = get_skip_list(nxs_in["entry"], skip_obj)
        # First copy full nxentry
        for k in nxs_in["entry"].keys():
            nxs_in["entry"].copy(k, nxentry)
        # Then delete objects from skip list
        for s in skip_list:
            del nxentry[s]
        return nxentry
    else:
        # Copy everything
        nxs_in.copy("entry", nxs_out)
        return


def identify_tristan_scan_axis(nxs_in: h5py.File) -> Tuple[str | None, Dict[str, Any]]:
    """
    Identify the scan_axis in the NeXus tree of a Tristan collection.

    Return the first data set in the group '/entry/data' that has the attribute
    'transformation_type' equal to 'rotation'.

    Args:
        nxs_in (h5py.File): Tristan NeXus file

    Returns:
        ax (str | None): Name of the scan_axis.
        ax_attrs (Dict[str, Any]): Attributes of the scan_axis dataset.
    """
    nxdata = nxs_in["entry/data"]
    for ax, h5_object in nxdata.items():
        if h5str(h5_object.attrs.get("transformation_type")) == "rotation":
            return ax, dict(h5_object.attrs)
    return None, {}


def convert_scan_axis(nxsample: h5py.Group, nxdata: h5py.Group, ax: str):
    """
    Modify all instances of scan_axis present in NeXus file NXsample group.

    Args:
        nxsample (h5py.Group): NXsample group of NeXus file to be modified.
        nxdata (h5py.Group): NXdata group of NeXus file to be modified.
        ax (str): Name of scan_axis.
    """
    del nxsample["transformations/" + ax]
    nxsample["transformations/" + ax] = nxdata[ax]
    name = (
        "sample_" + ax + "/" + ax if "sam" not in ax else "sample_" + ax[-1] + "/" + ax
    )
    del nxsample[name]
    nxsample[name] = nxdata[ax]


def find_chipmap_in_tristan_nxs(
    nxobj: h5py.File | h5py.Group, loc: str = "entry/source/notes/chipmap"
) -> bool:
    """
    Look for the saved chipmap for a SSX experiment inside a tristan nexus file.

    Args:
        nxobj (h5py.File | h5py.Group): NeXus object to be searched, could be a file or a group.
        loc (str, optional): Location where the chipmap should be saved. Defaults to "entry/source/notes/chipmap".

    Returns:
        bool: Returns True is a chipmap is found, False otherwise.
    """
    obj_list = walk_nxs(nxobj)
    if loc in obj_list:
        return True
    else:
        return False


def compute_ssx_axes(nxs_in, nbins, rot_ax, rot_val):
    # Get chipmap: use default chipmap location: /entry/source/notes/chipmap
    blocks = eval(nxs_in["/entry/source/notes/chipmap"][()])

    # Define chip
    chip_info = eval(nxs_in["/entry/source/notes/chip"][()])
    chip = Chip(
        "fastchip",
        num_steps=[chip_info["X_NUM_STEPS"], chip_info["Y_NUM_STEPS"]],
        step_size=[chip_info["X_STEP_SIZE"], chip_info["Y_STEP_SIZE"]],
        num_blocks=[chip_info["X_NUM_BLOCKS"], chip_info["Y_NUM_BLOCKS"]],
        block_size=[chip_info["X_BLOCK_SIZE"], chip_info["Y_BLOCK_SIZE"]],
        start_pos=[
            chip_info["X_START"],
            chip_info["Y_START"],
            chip_info["Z_START"],
        ],
    )

    # Get axis list
    axes_list = [k for k in nxs_in["/entry/sample/transformations"].keys()]
    x_idx = axes_list.index("sam_x")
    y_idx = axes_list.index("sam_y")

    # Calculate scan start/end positions on chip
    if (
        list(blocks.values())[0] == "fullchip"
        and nbins == chip.tot_windows_per_block() * chip.tot_blocks()
    ):
        # All windows in the whole chip have been scanned once
        start_pos, end_pos = compute_goniometer(chip, axes_list, full=True)
        num = (chip.num_steps[1], chip.num_steps[0])
    elif nbins == len(blocks) * chip.tot_windows_per_block():
        # All the windows in the selected blocks have been scanned once
        start_pos, end_pos = compute_goniometer(chip, axes_list, blocks=blocks)
        num = (chip.num_steps[1], chip.num_steps[0])
    else:
        # Either each window shot multiple times or binning over multiple windows. TBC.
        # if nbins == N*(len(blocks) * chip.tot_windows_per_block()) ---> see n_exposure thing from I24; nbins % () == 0, nbins / () = N_EXPOSURES
        # else do some sort of average over a bunch of windows.
        pass

    # Translation values
    TRANSL = {"sam_y": np.array([]), "sam_x": np.array([])}
    for s, e in start_pos.values(), end_pos.values():
        starts = [
            s[y_idx],
            s[x_idx],
        ]  # because I can't be sure they will be in the right order!
        ends = [
            e[y_idx] - chip.step_size[1],
            e[x_idx] - chip.step_size[0],
        ]  # because scanspec
        transl = calculate_scan_range(["sam_y", "sam_x"], starts, ends, n_images=num)
        TRANSL["sam_y"] = np.append(TRANSL["sam_y"], np.round(transl["sam_y"], 3))
        TRANSL["sam_x"] = np.append(TRANSL["sam_x"], np.round(transl["sam_x"], 3))

    # Rotation values
    OSC = calculate_scan_range(
        [rot_ax], [rot_val[0]], [rot_val[1]], n_images=nbins, rotation=True
    )
    return OSC, TRANSL
