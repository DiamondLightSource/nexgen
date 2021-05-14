"""
Utilities for writing new NeXus format files.
"""
import numpy as np

from .. import imgcif2mcstas


def split_vector_arrays(coord_frame, axes_names, array):
    """
    Args:
    Returns:
    """
    v = []
    for j in range(len(axes_names)):
        a = array[3 * j : 3 * j + 3]
        if coord_frame == "imgcif":
            v.append(imgcif2mcstas(a))
        else:
            v.append(tuple(a))
    return v


def calculate_origin(beam_center_fs, fs_pixel_size, fast_axis_vector, slow_axis_vector):
    """
    Calculates the detector origin which is saved into the module_offset fields.

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
