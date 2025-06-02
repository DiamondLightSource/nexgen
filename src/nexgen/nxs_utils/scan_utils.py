"""
Utilities to look for scan axes and calculate scan ranges from a list of Axis objects.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Dict, List, NamedTuple

from numpy.typing import ArrayLike
from scanspec.core import Path as ScanPath
from scanspec.specs import Line

from .axes import Axis

scan_logger = logging.getLogger("nexgen.ScanUtils")


# Some options for grid scans
class GridScanOptions(NamedTuple):
    """Options for defining a grid scan.

    Attributes:
        axes_order (tuple[str, str]): List of axes in order of (fast, slow).
        snaked (bool): Boolean to say whether it's a snaked scan.
    """

    axes_order: tuple[str, str]
    snaked: bool


class ScanDirection(IntEnum):
    POSITIVE = 1
    NEGATIVE = -1


class ScanAxisNotFoundError(Exception):
    def __init__(self, errmsg):
        scan_logger.error(errmsg)


class ScanAxisError(Exception):
    def __init__(self, errmsg):
        scan_logger.error(errmsg)


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
        ScanAxisNotFoundError: If no axes have been passed.
        ValueError: If more than one rotation axis seems to move.

    Returns:
        scan_axis (str): String identifying the rotation scan axis.
    """
    # This assumes that at least one axis is always passed.
    if len(axes_list) == 0:
        raise ScanAxisNotFoundError(
            "Impossible to determine oscillation scan axis. No axes passed to function. Please make sure at least one value is passed."
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
            raise ScanAxisNotFoundError(
                "Unable to correctly identify the rotation scan axis."
            )
        return rot_axes[scan_idx.index(True)].name


def identify_grid_scan_axes(
    axes_list: List[Axis],
) -> List[str]:
    """
    Identify the scan axes for a translation linear/grid scan.

    Args:
        axes_list (List[Axis]): List of axes objects associated to goniometer axes.

    Raises:
        ScanAxisNotFoundError: If no axes have been passed.

    Returns:
        scan_axis (List[str]): List of strings identifying the linear/grid scan axes. If no axes are identified, it will return an empty list.
    """
    if len(axes_list) == 0:
        raise ScanAxisNotFoundError(
            "Impossible to determine translation scan. No axes passed to function. Please make sure at least one value is passed."
        )

    # Look only at translation axes
    tr_axes = [ax for ax in axes_list if ax.transformation_type == "translation"]
    grid_axes = [ax.name for ax in tr_axes if ax.is_scan is True]
    return grid_axes


def calculate_scan_points(
    axis1: Axis,
    axis2: Axis | None = None,
    snaked: bool = True,
    rotation: bool = False,
    tot_num_imgs: int | None = None,
) -> Dict[str, ArrayLike]:
    """Calculate the scan range for a linear/grid scan or a rotation scan from the number of images (steps) to be written in each direction.

    When dealing with a rotation axis, if there are multiple images but no rotation scan, return the axis start position repeated as many times \
        as the number of images - either defined by the num_steps attribute of the Axis object or passed as tot_num_imgs.

    Args:
        axis1 (Axis): Axis object describing the axis involved in a scan.
        axis2 (Axis, optional): Axis object describing the second axis involved in a scan. Only necessary for a grid scan. Defaults to None.
        snaked (bool, optional):  If True, scanspec will "draw" a grid where the second axis is snaked. \
            It will be ignored for a rotation scan. Defaults to True.
        rotation (bool, optional): Tell the function to calculate a rotation scan. Defaults to False.
        tot_num_imgs (int, optional): Total number of images. Only used for oscillation axis when there is no rotation. \
            It will be ignored otherwise. Defaults to None.

    Raises:
        ScanAxisError: If the passed axis has the wrong transformation type.
        ValueError: For a rotation axis with no rotation, if the number of images is missing.

    Returns:
        Dict[str, ArrayLike]: A dictionary of ("axis_name": axis_range) key-value pairs.
    """

    if rotation is True:
        if axis1.transformation_type != "rotation":
            raise ScanAxisError(
                f"Wrong transformation type: a {axis1.transformation_type} has been passed for a rotation scan."
            )
        if axis1.num_steps == 0 and tot_num_imgs is None:
            raise ValueError(
                "Missing number of scan points, impossible to calculate scan."
            )

        n_images = tot_num_imgs if tot_num_imgs else axis1.num_steps
        spec = Line(axis1.name, axis1.start_pos, axis1.end_pos, n_images)
        scan_path = ScanPath(spec.calculate())

        return scan_path.consume().midpoints

    if axis1.transformation_type != "translation":
        raise ScanAxisError(
            f"Wrong transformation type: a {axis1.transformation_type} has been passed for a translation scan."
        )

    if axis2 and axis2.transformation_type != "translation":
        raise ScanAxisError(
            f"Wrong transformation type: a {axis2.transformation_type} has been passed for a translation scan."
        )

    if axis2 is None:
        spec = Line(
            axis1.name,
            axis1.start_pos,
            axis1.end_pos,
            axis1.num_steps,
        )
    elif axis2 and snaked is True:
        spec = Line(
            axis1.name,
            axis1.start_pos,
            axis1.end_pos,
            axis1.num_steps,
        ) * ~Line(
            axis2.name,
            axis2.start_pos,
            axis2.end_pos,
            axis2.num_steps,
        )
    else:
        spec = Line(
            axis1.name,
            axis1.start_pos,
            axis1.end_pos,
            axis1.num_steps,
        ) * Line(
            axis2.name,
            axis2.start_pos,
            axis2.end_pos,
            axis2.num_steps,
        )
    scan_path = ScanPath(spec.calculate())

    return scan_path.consume().midpoints
