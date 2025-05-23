"""
Utilities for copying metadata to new NeXus files.
"""

from __future__ import annotations

from typing import Any

import h5py
import numpy as np
from numpy.typing import ArrayLike

from ..beamlines.beamline_utils import PumpProbe
from ..beamlines.SSX_chip import Chip, compute_goniometer
from ..nxs_utils import Axis, TransformationType
from ..nxs_utils.scan_utils import calculate_scan_points
from ..nxs_write.write_utils import create_attributes
from ..utils import units_of_length, walk_nxs


def h5str(h5_value: str | np.bytes_ | bytes) -> str:
    """
    Convert a value returned an h5py attribute to str.

    h5py can return either a bytes-like (numpy.string_) or str object
    for attribute values depending on whether the value was written as
    fixed or variable length. This function collapses the two to str.

    Args:
        h5_value (str | np.bytes_ | bytes): Original attribute value.

    Returns:
        str: Attribute value collapsed to a str.
    """
    if isinstance(h5_value, (np.bytes_, bytes)):
        return h5_value.decode("utf-8")
    return h5_value


def get_skip_list(nxentry: h5py.Group, skip_obj: list[str]) -> list[str]:
    """
    Get a list of all the objects that should not be copied in the new NeXus file.

    Args:
        nxentry (h5py.Group): NXentry group of a NeXus file.
        skip_obj (list[str]): List of objects that should not be copied.

    Returns:
        skip_list (list[str]): List of "NXclass" objects to skip during copy.
    """
    obj_list = walk_nxs(nxentry)
    skip_list = []
    for obj in obj_list:
        try:
            if nxentry[obj].attrs["NX_class"] in np.bytes_(skip_obj):
                skip_list.append(obj)
        except Exception:
            pass
    return skip_list


def get_nexus_tree(
    nxs_in: h5py.File,
    nxs_out: h5py.File,
    skip: bool = True,
    skip_obj: list[str] = None,
) -> h5py.Group | None:
    """
    Copy the tree from the original NeXus file. Everything except NXdata is copied to a new NeXus file.
    If skip is False, then the full tree is copied.

    Args:
        nxs_in (h5py.File): Original NeXus file.
        nxs_out (h5py.File): New NeXus file.
        skip (bool, optional): Copy everything but objects in skip_obj, which always include NXdata.
                            Pass False to copy the whole NXentry tree. Defaults to True.
        skip_obj (list[str], optional): List of NX_class objects not to be copied, eg. 'NXdata' or 'NXdetector'.. Defaults to None.

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
        return None


def identify_tristan_scan_axis(nxs_in: h5py.File) -> tuple[str | None, dict[str, Any]]:
    """
    Identify the scan_axis in the NeXus tree of a Tristan collection.

    Return the first data set in the group '/entry/data' that has the attribute
    'transformation_type' equal to 'rotation'.

    Args:
        nxs_in (h5py.File): Tristan NeXus file

    Returns:
        ax (str | None): Name of the scan_axis.
        ax_attrs (dict[str, Any]): Attributes of the scan_axis dataset.
    """
    nxdata = nxs_in["entry/data"]
    for ax, h5_object in nxdata.items():
        if h5str(h5_object.attrs.get("transformation_type")) == "rotation":
            return ax, dict(h5_object.attrs)
    return None, {}


def convert_scan_axis(
    nxsample: h5py.Group, nxdata: h5py.Group, ax: str, ax_range: ArrayLike | None = None
):
    """
    Modify all instances of scan_axis present in NeXus file NXsample group.

    Args:
        nxsample (h5py.Group): NXsample group of NeXus file to be modified.
        nxdata (h5py.Group): NXdata group of NeXus file to be modified.
        ax (str): Name of scan_axis.
        ax_range (ArrayLike): Scan points. If passed, axis_increment_set and axis_end will also be written.\
            Defaults to None
    """
    del nxsample[f"transformations/{ax}"]
    nxsample[f"transformations/{ax}"] = nxdata[ax]
    grp_name = f"sample_{ax}" if "sam" not in ax else f"sample_{ax[-1]}"
    old_exists = grp_name in list(nxsample.keys())
    if old_exists:
        del nxsample[grp_name]
        nxsample[f"{grp_name}/{ax}"] = nxdata[ax]
    if ax_range is not None and "sam" not in ax:
        increment = round(ax_range[1] - ax_range[0], 3)
        end = ax_range + increment
        nxsample["transformations"].create_dataset(
            f"{ax}_increment_set", data=increment
        )
        nxsample["transformations"].create_dataset(f"{ax}_end", data=end)
        if old_exists:
            nxsample[f"{grp_name}/{ax}_increment_set"] = nxsample[
                f"transformations/{ax}_increment_set"
            ]
            nxsample[f"{grp_name}/{ax}_end"] = nxsample[f"transformations/{ax}_end"]


def check_and_fix_det_axis(nxs_in: h5py.File):
    det_z_grp = nxs_in["/entry/instrument/detector/transformations/detector_z"]
    det_z = det_z_grp["det_z"]
    if isinstance(det_z[()], bytes) or isinstance(det_z[()], str):
        det_z_attrs = {}
        for k, v in det_z.attrs.items():
            det_z_attrs[k] = v
        dist = float(det_z[()])
        dist = units_of_length(str(dist) + "mm")

        del nxs_in["/entry/instrument/detector/transformations/detector_z/det_z"]
        nxdet_z = det_z_grp.create_dataset("det_z", data=np.array([dist.magnitude]))
        for k, v in det_z_attrs.items():
            nxdet_z.attrs.create(k, v)

        del nxs_in["/entry/instrument/detector/distance"]
        nxs_in["/entry/instrument/detector"].create_dataset(
            "distance", data=dist.to("m").magnitude
        )
        nxs_in["/entry/instrument/detector/distance"].attrs.create(
            "units", np.bytes_("m")
        )
    else:
        return


def is_chipmap_in_tristan_nxs(
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


def compute_ssx_axes(
    nxs_in: h5py.File, nbins: int, rot_ax: str, rot_val: tuple | list | ArrayLike
) -> tuple[dict, dict, dict, int | None]:
    """
    Computes the positions on chip corresponding to the binned images from a Tristan fixed target collection.

    The function looks for the blocks (chipmap) and the chip_info dictionaries inside the original NeXus file and calculates the scan points from there.
    For older versions of the SSX NeXus files, this information is not available and the scan points will be calculated based on the number of images and
    using the default Oxford chip dimensions, starting from the upper left corned of the chip.
    If multiple windows have been binned into a single image, instead of the sam_(x,y) translation axes values, the number of windows per images will
    be returned and saved in the NeXus file.

    Args:
        nxs_in (h5py.File): File handle for the original Tristan collection NeXus file.
        nbins (int): Number of images.
        rot_ax (str): Rotation axis.
        rot_val (tuple | list | ArrayLike): Rotation axis start and stop values, as found in the original NeXus.

    Returns:
        OSC, TRANSL, pump_info, windows_per_bin (tuple[dict, dict, dict, int | None]): Oscillation range, Translation range, pump_probe info, number of windows per binned image.
    """
    # Define pump_probe
    pp = PumpProbe()
    pp.status = True

    # Get chipmap: use default chipmap location: /entry/source/notes/chipmap if there
    if is_chipmap_in_tristan_nxs(nxs_in) is True:
        blocks = eval(nxs_in["/entry/source/notes/chipmap"][()])
        chip_info = eval(nxs_in["/entry/source/notes/chip"][()])
        pp.exposure = chip_info["LASER_DWELL"]
        pp.delay = chip_info["LASER_DELAY"]
    else:
        # Older version of these files don't have any chip information inside.
        from ..beamlines.SSX_chip import CHIP_DICT_DEFAULT

        chip_info = {k: v[1] for k, v in CHIP_DICT_DEFAULT.items()}
        # Assume 400 imgs each block in the chip
        n_blocks = nbins // 400
        key = [f"%0{2}d" % bl for bl in range(1, n_blocks + 1)]
        val = []
        for i in range(chip_info["X_NUM_BLOCKS"]):
            for j in range(chip_info["Y_NUM_BLOCKS"]):
                val.append((i, j))
        blocks = {key[i]: val[i] for i in range(len(key))}
        pp.exposure = nxs_in["/entry/source/notes/pump_exposure_time"][()]
        pp.delay = nxs_in["/entry/source/notes/pump_delay"][()]

    # Define chip
    chip = Chip(
        "fastchip",
        num_steps=(chip_info["X_NUM_STEPS"], chip_info["Y_NUM_STEPS"]),
        step_size=(chip_info["X_STEP_SIZE"], chip_info["Y_STEP_SIZE"]),
        num_blocks=(chip_info["X_NUM_BLOCKS"], chip_info["Y_NUM_BLOCKS"]),
        block_size=(chip_info["X_BLOCK_SIZE"], chip_info["Y_BLOCK_SIZE"]),
        start_pos=(
            chip_info["X_START"],
            chip_info["Y_START"],
            chip_info["Z_START"],
        ),
    )

    # Rotation values
    osc_ax = Axis(
        rot_ax,
        "",
        TransformationType.ROTATION,
        (0, 0, 0),
        start_pos=rot_val[0],
    )
    OSC = calculate_scan_points(osc_ax, rotation=True, tot_num_imgs=nbins)

    num_blocks = (
        chip.tot_blocks() if list(blocks.values())[0] == "fullchip" else len(blocks)
    )

    # Calculate scan start/end positions on chip
    N_EXP = chip_info["N_EXPOSURES"]
    if nbins % (num_blocks * chip.tot_windows_per_block()) == 0:
        # All the windows in the selected blocks (full chip or not) have been scanned at least once.
        N_EXP = nbins // (num_blocks * chip.tot_windows_per_block())

        axis1 = Axis("sam_y", "", TransformationType.TRANSLATION, (0, 0, 0))
        axis2 = Axis("sam_x", "", TransformationType.TRANSLATION, (0, 0, 0))
        start_pos = compute_goniometer(chip, blocks=blocks, ax1="sam_y", ax2="sam_x")

        # Translation values
        TRANSL = {"sam_y": np.array([]), "sam_x": np.array([])}
        for k, v in start_pos.items():
            axis1.start_pos = v[axis1.name]
            axis1.increment = chip.step_size[1] * v["direction"]
            axis1.num_steps = chip.num_steps[1]
            axis2.start_pos = v[axis2.name]
            axis2.increment = chip.step_size[0]
            axis2.num_steps = chip.num_steps[0]

            transl = calculate_scan_points(axis1, axis2)

            TRANSL["sam_y"] = np.append(TRANSL["sam_y"], np.round(transl["sam_y"], 3))
            TRANSL["sam_x"] = np.append(TRANSL["sam_x"], np.round(transl["sam_x"], 3))

        if N_EXP > 1:
            OSC = {k: [val for val in v for _ in range(N_EXP)] for k, v in OSC.items()}
            TRANSL = {
                k: [val for val in v for _ in range(N_EXP)] for k, v in TRANSL.items()
            }

        # Update pump probe
        pump_info = pp.model_dump()
        pump_info["n_exposures"] = N_EXP
        return OSC, TRANSL, pump_info, None
    else:
        # Hopefully this will not happen..
        # Do not set N_EXP, there should be no repeat here
        # Find out how many consecutive windows are binned together.
        windows_per_bin = (num_blocks * chip.tot_windows_per_block()) // nbins
        return OSC, {}, pp.model_dump(), windows_per_bin
