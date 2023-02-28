"""
Utilities to look for scan axes and calculate scan ranges from a list of Axis objects.
"""

from __future__ import annotations

from typing import Dict, List

from numpy.typing import ArrayLike

from .Axes import Axis

# from scanspec.core import Path as ScanPath
# from scanspec.specs import Line


class ScanNotFoundError(Exception):
    pass


def identify_osc_axis(
    axes_list: List[Axis],
    default: str = "omega",
) -> str:
    """
    Identify the rotation scan_axis.

    This function identifies the scan axis from the list passed as argument.
    The scan axis is the one where start and end value are not the same.
    If there is only one rotation axis, that is the one returned.
    In the case scan axis cannot be identified, a default value is arbitrarily assigned.

    Args:
        axes_list (List[Axis]): List of axes objects associated to goniometer axes.
        default (str, optional): String to deafult to in case scan axis is not found. Defaults to "omega".

    Raises:
        ValueError: If no axes have been passed.
        ValueError: If more than one rotation axis seems to move.

    Returns:
        scan_axis (str): String identifying the rotation scan axis.
    """
    # This assumes that at least one axis is always passed.
    if len(axes_list) == 0:
        raise ValueError(
            "Impossible to determine oscillation scan axis. No axes passed to find_osc_axis function. Please make sure at least one value is passed."
        )
    # Look only for rotation axes
    rot_axes = [ax for ax in axes_list if ax.transformation_type == "rotation"]
    if len(rot_axes) == 1:
        return rot_axes[0].name
    else:
        scan_idx = [ax.is_scan for ax in rot_axes]
        if scan_idx.count(True) == 0:
            return default
        if scan_idx.count(True) > 1:
            raise ValueError("Unable to correctly identify the rotation scan axis.")
        return rot_axes[scan_idx.index(True)].name


def identify_grid_scan_axes(
    axes_list: List[Axis],
) -> List[str]:
    """
    Identify the scan axes for a translation linear/grid scan.

    Args:
        axes_list (List[Axis]): List of axes objects associated to goniometer axes.

    Raises:
        ValueError: If no axes have been passed.

    Returns:
        scan_axis (List[str]): List of strings identifying the linear/grid scan axes. If no axes are identified, it will return an empty list.
    """
    if len(axes_list) == 0:
        raise ValueError(
            "Impossible to determine translation scan. No axes passed to find_grid_scan_axes function. Please make sure at least one value is passed."
        )

    # Look only at translation axes
    tr_axes = [ax for ax in axes_list if ax.transformation_type == "translation"]
    grid_axes = [ax.name for ax in tr_axes if ax.is_scan is True]
    return grid_axes


def calculate_scan(
    axes_list: List[Axis],
    snaked: bool = False,
    rotation: bool = False,
    tot_num_imgs: int | None = None,
) -> Dict[str, ArrayLike]:
    """Calculate the scan range for a linear/grid scan or a rotation scan from the number of images to be written.

    When dealing with a rotation axis, if there are multiple images but no rotation scan, return axis_start repeated n_images times.

    Args:
        axes_list (List[Axis]): List of axes objects associated to goniometer axes.
        snaked (bool, optional):  If True, scanspec will "draw" a snaked grid. Defaults to False.
        rotation (bool, optional): Tell the function to calculate a rotation scan. Defaults to False.
        tot_num_imgs (int, optional): Total number of images. Only used for oscillation axis when there is no rotation.
            It will be ignored otherwise. Defaults to None.

    Raises:
        ScanNotFoundError: When an empty axes names list has been passed.

    Returns:
        Dict[str, ArrayLike]: A dictionary of ("axis_name": axis_range) key-value pairs.
    """
    # Come cavolo faccio con la rotazione non so proprio
    pass
