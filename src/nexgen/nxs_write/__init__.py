"""
Utilities for writing new NeXus format files.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import h5py
import numpy as np
from h5py import AttributeManager
from scanspec.core import Path as ScanPath
from scanspec.specs import Line


def create_attributes(nxs_obj: h5py.Group | h5py.Dataset, names: Tuple, values: Tuple):
    """
    Create or overwrite attributes with additional metadata information.

    Args:
        nxs_obj:    NeXus object (Group or Dataset) to which the attributes should be attached
        names:      Tuple containing the names of the new attributes
        values:     Tuple containing the values relative to the names
    """
    for n, v in zip(names, values):
        if type(v) is str:
            # If a string, convert to numpy.string_
            v = np.string_(v)
        AttributeManager.create(nxs_obj, name=n, data=v)


def set_dependency(dep_info: str, path: str = None):
    """
    Define value for "depends_on" attribute.
    If the attribute points to the head of the dependency chain, simply pass "." for dep_info.

    Args:
        dep_info (str): The name of the transformation upon which the current one depends on.
        path (str): Where the transformation is. Set to None, if passed it points to location in the NeXus tree.
    Returns:
        The value to be passed to the attribute "depends_on"
    """
    if dep_info == ".":
        return np.string_(".")
    if path:
        if path.endswith("/") is False:
            path += "/"
        return np.string_(path + dep_info)
    else:
        return np.string_(dep_info)


def find_osc_axis(
    axes_names: List,
    axes_starts: List,
    axes_ends: List,
    axes_types: List,
    default: str = "omega",
) -> str:
    """
    Identify the rotation scan_axis.

    This function identifies the scan axis from the list passed as argument.
    The scan axis is the one where start and end value are not the same.
    If there is only one rotation axis, that is the one returned.
    In the case scan axis cannot be identified, a default value is arbitrarily assigned.

    Args:
        axes_names (list): List of names associated to goniometer axes.
        axes_starts (list): List of start values.
        axes_ends (list): List of end values.
        axes_types (list): List of axes types, useful to identify only the rotation axes.
        default (str): String to deafult to in case scan axis is not found.
    Returns:
        scan_axis (str): String identifying the rotation scan axis.
    """
    # This assumes that at least one rotation axis is always passed.
    # Assuming all list are of the same length ...
    if len(axes_names) == 0:
        raise ValueError(
            "Impossible to determine translation scan. No axes passed to find_osc_axis function. Please make sure at least one value is passed."
        )
    # assert len(axes_names) > 0, "Please pass at least one axis."
    # Look only for rotation axes
    rot_idx = [i for i in range(len(axes_types)) if axes_types[i] == "rotation"]
    axes_names = [axes_names[j] for j in rot_idx]
    axes_starts = [axes_starts[j] for j in rot_idx]
    axes_ends = [axes_ends[j] for j in rot_idx]

    if len(axes_names) == 1:
        scan_axis = axes_names[0]
    else:
        idx = [(i != j) for i, j in zip(axes_starts, axes_ends)]
        if idx.count(True) == 0:
            # just in case ...
            scan_axis = default
        elif idx.count(True) == 1:
            scan_axis = axes_names[idx.index(True)]
        else:
            raise ValueError("Unable to correctly identify the rotation scan axis.")
    return scan_axis


def find_grid_scan_axes(
    axes_names: List,
    axes_starts: List,
    axes_ends: List,
    axes_types: List,
) -> List[str]:
    """
    Identify the scan axes for a linear/grid scan.

    Args:
        axes_names (List): List of names associated to goniometer axes.
        axes_starts (List): List of start values.
        axes_ends (List): List of end values.
        axes_types (List): List of axes types, useful to identify only the translation axes.

    Returns:
        scan_axis (List[str]): List of strings identifying the linear/grid scan axes. If no axes are identified, it will return an empty list.
    """
    if len(axes_names) == 0:
        raise ValueError(
            "Impossible to determine translation scan. No axes passed to find_grid_scan_axes function. Please make sure at least one value is passed."
        )

    # Look only at translation axes
    grid_idx = [i for i in range(len(axes_names)) if axes_types[i] == "translation"]
    axes_names = [axes_names[j] for j in grid_idx]
    axes_starts = [axes_starts[j] for j in grid_idx]
    axes_ends = [axes_ends[j] for j in grid_idx]

    scan_axis = []
    for n, ax in enumerate(axes_names):
        if axes_starts[n] != axes_ends[n]:
            scan_axis.append(ax)
    return scan_axis


def calculate_scan_range(
    axes_names: List,
    axes_starts: List,
    axes_ends: List,
    axes_increments: List = None,
    n_images: Tuple | int = None,
    snaked: bool = True,
    rotation: bool = False,
) -> Dict[str, np.ndarray]:
    """
    Calculate the scan range for a linear/grid scan or a rotation scan from the number of images to be written.
    If the number of images is not provided, it can be calculated from the increment value of the axis (these values are mutually exclusive).
    When dealing with a rotation axis, if there are multiple images but no rotation scan, return axis_start repeated n_images times.

    Args:
        axes_names (List): List of names for the axes involved in the scan.
        axes_starts (List): List of axis positions at the beginning of the scan.
        axes_ends (List): List of axis positions at the end of the scan.
        axes_increments (List, optional): List of ranges through which the axes move each frame. Mostly used for rotation scans. Defaults to None.
        n_images (Tuple | int, optional): Number of images to be written. If writing a 2D scan, it should be a (nx, ny) tuple, \
                                        where tot_n_img=nx*ny, any int value is at this time ignored. Defaults to None.
        snaked (bool): If True, scanspec will "draw" a snaked grid. Defaults to True.
        rotation (bool): Tell the function to calculate a rotation scan. Defaults to False.

    Raises:
        TypeError: If the input axes are not lists.
        ValueError: When an empty axes names list has been passed.
        ValueError: When both axes_increments and n_images have been passed. The two values are mutually exclusive.
        ValueError: When neither axes_increments not n_images have been passed.
        ValueError: For a grid scan, if axes_increments is None, n_images must be a tuple of len=2 to be sure to accurately calculate the scan points.

    Returns:
        Dict[str, np.ndarray]: A dictionary of ("axis_name": axis_range) key-value pairs.
    """
    if type(axes_names) != list or type(axes_starts) != list or type(axes_ends) != list:
        raise TypeError("Input values for axes must be passed as lists.")

    if len(axes_names) == 0:
        raise ValueError("No axes have been passed, impossible to determine scan.")

    if n_images and axes_increments:
        raise ValueError(
            "The axes_increments and n_images arguments are mutually exclusive. Please pass just one of those."
            "For a 2D scan it is recommended that n_images is passed."
        )
    elif not n_images and not axes_increments:
        raise ValueError(
            "Impossible to calculate scan points, please pass either the axes increment values or the number of scan points (n_images) per axis."
            "For a 2D scan it is recommended that n_images is passed."
        )

    if len(axes_names) == 1 and rotation is True:
        if not n_images:
            n_images = round(abs(axes_starts[0] - axes_ends[0]) / axes_increments[0])

        if axes_starts[0] != axes_ends[0] and axes_increments:
            axes_ends[0] = axes_ends[0] - axes_increments[0]
        elif axes_starts[0] != axes_ends[0] and not axes_increments:
            inc = (axes_ends[0] - axes_starts[0]) / n_images
            axes_ends[0] = axes_ends[0] - inc

        spec = Line(axes_names[0], axes_starts[0], axes_ends[0], n_images)
        scan_path = ScanPath(spec.calculate())

    elif len(axes_names) == 1 and rotation is False:
        if not n_images:
            # FIXME This calculation still gives the wrong increment between scan points.
            n_images = (
                round(abs(axes_starts[0] - axes_ends[0]) / axes_increments[0]) + 1
            )
        elif type(n_images) is tuple and len(n_images) == 1:
            # This is mostly a double paranoid check
            n_images = n_images[0]

        spec = Line(axes_names[0], axes_starts[0], axes_ends[0], n_images)
        scan_path = ScanPath(spec.calculate())

    else:
        if not n_images:
            # FIXME This calculation still gives the wrong increment between scan points.
            n_images0 = (
                round(abs(axes_starts[0] - axes_ends[0]) / axes_increments[0]) + 1
            )
            n_images1 = (
                round(abs(axes_starts[1] - axes_ends[1]) / axes_increments[1]) + 1
            )
        elif len(n_images) == 1:
            raise ValueError(
                "Impossible to correctly calculate scan points from just the total number of images."
                "Please either pass a tuple with the number of scan point per axis or the axes increments."
            )
        else:
            n_images0 = n_images[0]
            n_images1 = n_images[1]

        if snaked is True:
            spec = Line(axes_names[0], axes_starts[0], axes_ends[0], n_images0) * ~Line(
                axes_names[1], axes_starts[1], axes_ends[1], n_images1
            )
        else:
            spec = Line(axes_names[0], axes_starts[0], axes_ends[0], n_images0) * Line(
                axes_names[1], axes_starts[1], axes_ends[1], n_images1
            )
        scan_path = ScanPath(spec.calculate())

    return scan_path.consume().midpoints


def calculate_origin(
    beam_center_fs: List | Tuple,
    fs_pixel_size: List | Tuple,
    fast_axis_vector: Tuple,
    slow_axis_vector: Tuple,
    mode: str = "1",
):
    """
    Calculate the offset of the detector.

    This function returns the detector origin array, which is saved as the vector attribute of the module_offset field.
    The value to set the module_offset to is also returned: the magnitude of the displacement if the vector is normalized, 1.0 otherwise
    Assumes that fast and slow axis vectors have already been converted to mcstas if needed.

    Args:
        beam_center_fs:     List or tuple of beam center position in fast and slow direction.
        fs_pixel_size:      List or tuple of pixel size in fast and slow direction, in m.
        fast_axis_vector:   Fast axis vector (usually passed as a tuple).
        slow__axis_vector:  Slow axis vector ( usually passed as a tuple).
        mode:               Decides how to calculate det_origin.
                            If set to "1" the displacement vector is un-normalized and the offset value set to 1.0.
                            If set to "2" the displacement is normalized and the offset value is set to the magnitude of the displacement.
    Returns:
        det_origin:         Displacement of beam center, vector attribute of module_offset.
        offset_value:       Value to assign to module_offset, depending whether det_origin is normalized or not.
    """
    # what was calculate module_offset
    x_scaled = beam_center_fs[0] * fs_pixel_size[0]
    y_scaled = beam_center_fs[1] * fs_pixel_size[1]
    # Detector origin
    det_origin = x_scaled * np.array(fast_axis_vector) + y_scaled * np.array(
        slow_axis_vector
    )
    det_origin = list(-det_origin)
    if mode == "1":
        offset_val = 1.0
    else:
        offset_val = math.hypot(*det_origin[:-1])
    return det_origin, offset_val


def find_number_of_images(datafile_list: List[Path]) -> int:
    """
    Calculate total number of images when there's more than one input HDF5 file.

    Args:
        datafile_list (List[Path]): List of paths to the input image files.

    Returns:
        num_images (int): Total number of images._summary_
    """
    num_images = 0
    for filename in datafile_list:
        with h5py.File(filename, "r") as f:
            num_images += f["data"].shape[0]
    return int(num_images)
