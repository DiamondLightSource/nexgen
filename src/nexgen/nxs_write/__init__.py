"""
Utilities for writing new NeXus format files.
"""
import sys
import math
import h5py
import numpy as np

from pathlib import Path
from h5py import AttributeManager
from typing import List, Tuple, Union


def create_attributes(
    nxs_obj: Union[h5py.Group, h5py.Dataset], names: Tuple, values: Tuple
):
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
        dep_info:   The name of the transformation upon which the current one depends on.
        path:       Where the transformation is. Set to None, if passed it points to location in the NeXus tree.
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


def find_scan_axis(axes_names: List, axes_starts: List, axes_ends: List) -> str:
    """
    Identify the scan_axis.

    This function identifies the scan axis from the list passed as argument.
    The scan axis is the one where start and end value are not the same.
    If there is only one axis, that is the one returned.
    In the case of stills, phi is arbitrarily assigned.

    Args:
        axes_names:     List of names associated to goniometer axes.
        axes_starts:    List of start values.
        axes_ends:      List of end values.
    Returns:
        scan_axis:      String identifying the scan axis.
    """
    # TODO Handle multiple scan axes (2D scan).
    # Randomly assign to phi if stills
    assert len(axes_names) > 0, "Please pass at least one axis."
    if len(axes_names) == 1:
        scan_axis = axes_names[0]
    else:
        idx = [(i != j) for i, j in zip(axes_starts, axes_ends)]
        if idx.count(True) == 0:
            scan_axis = "phi"
        elif idx.count(True) == 1:
            scan_axis = axes_names[idx.index(True)]
        else:
            sys.exit("Unable to correctly identify the scan axis.")
    return scan_axis


def calculate_scan_range(
    axis_start: float,
    axis_end: float,
    axis_increment: float = None,
    n_images: int = None,
) -> np.ndarray:
    """
    Calculate the scan range for a rotation collection and return as a numpy array.

    axes_increments and n_images are mutually exclusive
    Args:
        axis_start:         Rotation axis position at the beginning of the scan, float.
        axis_end:           Rotation axis position at the end of the scan, float.
        axis_increment:     Range through which the axis moves each frame, float.
        n_images:           Alternatively, number of images, int.
    Returns:
        scan_range:         Numpy array of values for the rotation axis.
    """
    if n_images:
        scan_range = np.linspace(axis_start, axis_end, n_images)
    else:
        scan_range = np.arange(axis_start, axis_end, axis_increment)
    return scan_range


def calculate_origin(
    beam_center_fs: Union[List, Tuple],
    fs_pixel_size: Union[List, Tuple],
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


def find_number_of_images(datafile_list: List[Path]):
    """
    Calculate total number of images when there's more than one input HDF5 file.

    Args:
        datafiles:  List of paths to the input image files.
    Returns:
        num_images: Total number of images.
    """
    num_images = 0
    for filename in datafile_list:
        with h5py.File(filename, "r") as f:
            num_images += f["data"].shape[0]
    return num_images
