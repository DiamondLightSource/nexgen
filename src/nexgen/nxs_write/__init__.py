"""
Utilities for writing new NeXus format files.
"""
import sys
import numpy as np

from .. import imgcif2mcstas


def split_arrays(coord_frame, axes_names, array):
    """
    Split a list of values into arrays.

    This function splits up the list of values passed as phil parameters for vector, offset of all existing axes. If the coordinate frame is set to imgCIF, the arrays will have to be converted into mcstas.
    Args:
        coord_frame:    The coordinate system in which we are working: mcstas or imgCIF
        axes_names:     List of axes that have been passed as phil parameters
        array:          List of values to be split up
    Returns:
        array_dict:     Dictionary of arrays corresponding to each axis. Keys are axes names.
    """
    # array_list = []
    array_dict = {}
    for j in range(len(axes_names)):
        a = array[3 * j : 3 * j + 3]
        if coord_frame == "imgcif":
            # array_list.append(imgcif2mcstas(a))
            array_dict[axes_names[j]] = imgcif2mcstas(a)
        else:
            # array_list.append(tuple(a))
            array_dict[axes_names[j]] = tuple(a)
    return array_dict


def find_scan_axis(axes_names, axes_starts, axes_ends):
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
    # TODO handle multiple rotation (is that even doable?)
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


def calculate_scan_range(axis_start, axis_end, axis_increment=None, n_images=None):
    """
    Calculate the scan range for a rotation collection and return as a list.

    axes_increments and n_images are mutually exclusive
    Args:
        axis_start:
        axis_end:
        axis_increment:
        n_images:
    Returns:
        scan_range:         List of values for the scan axis.
    """
    # TODO add check that either N or axis increment is None
    if n_images:
        scan_range = np.linspace(axis_start, axis_end, n_images)
    else:
        scan_range = np.arange(axis_start, axis_end, axis_increment)
    return scan_range


def calculate_origin(beam_center_fs, fs_pixel_size, fast_axis_vector, slow_axis_vector):
    """
    Calculates the offset of the detector.

    This function returns the detector origin array, which is saved into the module_offset fields.
    Assumes that fast and slow axis vectors have already been converted to mcstas if needed.

    Args:
        beam_center_fs:     List or tuple of beam center position in fast and slow direction.
        fs_pixel_size:      List or tuple of pixel size in fast and slow direction, in m.
        fast_axis_vector:   Fast axis vector.
        slow__axis_vector:  Slow axis vector.
    Returns:
        det_origin:         Offset attribute of module_offset.
    """
    # what was calculate module_offset
    x_scaled = beam_center_fs[0] * fs_pixel_size[0]
    y_scaled = beam_center_fs[1] * fs_pixel_size[1]
    # Detector origin
    det_origin = x_scaled * np.array(fast_axis_vector) + y_scaled * np.array(
        slow_axis_vector
    )
    det_origin = list(-det_origin)
    return det_origin
