"""
Utilities for writing new NeXus format files.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

# import h5py
import numpy as np
from hdf5plugin import Bitshuffle
from numpy.typing import ArrayLike

# from h5py import AttributeManager
from scanspec.core import Path as ScanPath
from scanspec.specs import Line

import h5py  # isort: skip
from h5py import AttributeManager  # isort: skip


def create_attributes(nxs_obj: h5py.Group | h5py.Dataset, names: Tuple, values: Tuple):
    """
    Create or overwrite attributes with additional metadata information.

    Args:
        nxs_obj (h5py.Group | h5py.Dataset): NeXus object to which the attributes should be attached.
        names (Tuple): The names of the new attributes.
        values (Tuple): The attribute values asociated to the names.
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
        axes_names (List): List of names associated to goniometer axes.
        axes_starts (List): List of start values.
        axes_ends (List): List of end values.
        axes_types (List): List of axes types, useful to identify only the rotation axes.
        default (str, optional): String to deafult to in case scan axis is not found. Defaults to "omega".

    Raises:
        ValueError: If no axes have been passed.
        ValueError: If more than one rotation axis seems to move.

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

    Raises:
        ValueError: If no axes have been passed.

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
) -> Dict[str, ArrayLike]:
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
        Dict[str, ArrayLike]: A dictionary of ("axis_name": axis_range) key-value pairs.
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
            if axes_starts[0] > axes_ends[0]:
                # Account for reverse rotation.
                axes_ends[0] = axes_ends[0] + axes_increments[0]
            else:
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
) -> Tuple[List, float]:
    """
    Calculate the offset of the detector.

    This function returns the detector origin array, which is saved as the vector attribute of the module_offset field.
    The value to set the module_offset to is also returned: the magnitude of the displacement if the vector is normalized, 1.0 otherwise
    Assumes that fast and slow axis vectors have already been converted to mcstas if needed.

    Args:
        beam_center_fs (List | Tuple): Beam center position in fast and slow direction.
        fs_pixel_size (List | Tuple): Pixel size in fast and slow direction, in m.
        fast_axis_vector (Tuple): Fast axis vector.
        slow_axis_vector (Tuple): Slow axis vector.
        mode (str, optional): Decide how origin should be calculated.
                            If set to "1" the displacement vector is un-normalized and the offset value set to 1.0.
                            If set to "2" the displacement is normalized and the offset value is set to the magnitude of the displacement.
                            Defaults to "1".

    Returns:
        det_origin (List): Displacement of beam center, vector attribute of module_offset.
        offset_val (float): Value to assign to module_offset, depending whether det_origin is normalized or not.
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


def find_number_of_images(datafile_list: List[Path], entry_key: str = "data") -> int:
    """
    Calculate total number of images when there's more than one input HDF5 file.

    Args:
        datafile_list (List[Path]): List of paths to the input image files.
        entry_key (str):    Key for the location of the images inside the data files. Defaults to "data".

    Returns:
        num_images (int): Total number of images.
    """
    num_images = 0
    for filename in datafile_list:
        with h5py.File(filename, "r") as f:
            num_images += f[entry_key].shape[0]
    return int(num_images)


# Copy and compress a dataset inside a specified NXclass
def write_compressed_copy(
    nxgroup: h5py.Group,
    dset_name: str,
    data: ArrayLike = None,
    filename: Path | str = None,
    dset_key: str = None,
    block_size: int = 0,
):
    """
    Write a compressed copy of some dataset in the desired HDF5 group, using the Bitshuffle filter with lz4 compression.
    The main application for this function in nexgen is to write a compressed copy of a pixel mask or a flatfield file/dataset \
    directly into the NXdetector group of a NXmx NeXus file.
    The data and filename arguments are mutually exclusive as only one of them can be used as input.
    If a filename is passed, it is also required to pass the key for the relevant dataset to be copied. Failure to do so will result \
    in nothing being written to the NeXus file.

    Args:
        nxgroup (h5py.Group): Handle to HDF5 group.
        dset_name (str): Name of the new dataset to be written.
        data (ArrayLike, optional): Dataset to be compressed. Defaults to None.
        filename (Path | str, optional): Filename containing the dataset to be compressed into the NeXus file. Defaults to None.
        dset_key (str, optional): Dataset name inside the passed file. Defaults to None.
        block_size (int, optional): Number of elements per block, it needs to be divisible by 8. Defaults to 0.

    Raises:
        ValueError: If both a dataset and a filename have been passed to the function.
    """
    from .NXclassWriters import NXclass_logger

    if data is not None and filename is not None:
        raise ValueError(
            "The dset and filename arguments are mutually exclusive."
            "Please pass only the one from which the data should be copied."
        )
    if filename and not dset_key:
        NXclass_logger.warning(
            f"Missing key to find the dataset to be copied inside {filename}. {dset_name} will not be written into the NeXus file."
        )
        return

    if filename:
        with h5py.File(filename, "r") as fh:
            data = fh[dset_key][()]

    nxgroup.create_dataset(
        dset_name, data=data, **Bitshuffle(nelems=block_size, lz4=True)
    )
    NXclass_logger.info(
        f"A compressed copy of the {dset_name} has been written into the NeXus file."
    )
