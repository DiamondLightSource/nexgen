"""
Experiment definitions for SSX collections:
    - extruder
    - fixed target
    - 3D grid scan
"""

from __future__ import annotations

import logging

import numpy as np

from ..nxs_utils import Axis, TransformationType
from ..nxs_utils.scan_utils import calculate_scan_points
from .beamline_utils import PumpProbe
from .SSX_chip import (
    Chip,
    compute_goniometer,
    fullchip_blocks_conversion,
    read_chip_map,
)

__all__ = ["run_extruder", "run_fixed_target", "run_3D_grid_scan"]

# Define a logger object
logger = logging.getLogger("nexgen.SSX.run_expt")


def run_extruder(
    goniometer_axes: list[Axis],
    num_imgs: int,
    pump_probe: PumpProbe,
    osc_axis: str = "omega",
) -> tuple[list, dict, dict]:
    """Run the goniometer computations for an extruder experiment.

    Args:
        goniometer_axes (list[Axis]): List of goniometer axes for current beamline.
        num_imgs (int): Total number of images.
        pump_probe (PumpProbe): Pump probe parameters.
        osc_axis: Defines which axis is considered the "moving" one. Defaults to omega.

    Returns:
        tuple[list, dict, dict]:
            goniometer_axes: updated goniometer_axes list with actual values from the scan.
            SCAN: dictionary with oscillation scan axis values.
            pump_info: updated pump probe information.
    """
    logger.debug("Running an extruder experiment.")

    logger.debug("All axes are fixed, setting increments to 0.0 and starts == ends.")
    for ax in goniometer_axes:
        # Sanity check that no increment is greater than 0.0
        if ax.transformation_type == "rotation":
            ax.increment = 0.0

    # Identify the "oscillation axis"
    osc_idx = [n for n, ax in enumerate(goniometer_axes) if ax.name == osc_axis][0]
    goniometer_axes[osc_idx].num_steps = num_imgs

    # Calculate scan
    logger.debug(
        "Getting 'oscillation scan': roation axis not moving, same value for each image as."
    )
    SCAN = calculate_scan_points(
        goniometer_axes[osc_idx], rotation=True, tot_num_imgs=num_imgs
    )

    pump_info = pump_probe.model_dump()
    logger.debug("Removing pump_repeat from pump probe necessary information.")
    pump_info.pop("pump_repeat")

    return goniometer_axes, SCAN, pump_info


def run_fixed_target(
    goniometer_axes: list[Axis],
    chip_info: dict[str, list],
    pump_probe: PumpProbe,
    chipmap: list[int] | None = None,
    scan_axes: list[str, str] = ["sam_y", "sam_x"],
) -> tuple[dict, dict]:
    """Run the goniometer computations for a fixed-target experiment.

    Args:
        goniometer_axes (list[Axis]): List of goniometer axes for current beamline.
        chip_info (dict[str, list]): General information about the chip: number and size of blocks, \
            size and step of each window, start positions, number of exposures.
        pump_probe (PumpProbe): Pump probe parameters.
        chipmap (list[int], optional): List of blocks scanned. If None is passed, assumes a fullchip.
        scan_axes (list[str, str], optional): List of scan axes, in order slow,fast. \
            Defaults to ["sam_y", "sam_x"].

    Raises:
        ValueError: If one or both of the axes names passed as input are not part of the goniometer axes.
        ValueError:if chip_info hasn't been passed or is an empty dictionary.

    Returns:
        tuple[dict, dict]:
            SCAN: Dictionary with grid scan values.
            pump_info: Updated pump probe information.
    """
    logger.info("Running a fixed target experiment.")

    # Check that the axes for the scan make sense
    check_list = [n for n, ax in enumerate(goniometer_axes) if ax.name in scan_axes]
    if len(check_list) < len(scan_axes):
        raise ValueError(
            "Axis not found in the list of goniometer axes. Please check your input."
            f"Goniometer axes: {goniometer_axes}. Looking for {scan_axes}."
        )

    # Check that the chip dict has been passed, raise error if not
    if not chip_info:
        logger.error("No chip_dict found.")
        raise ValueError(
            "No information about the FT chip has been passed. \
            Impossible to determine scan parameters. NeXus file won't be written."
        )

    # Define chip
    chip = Chip(
        "fastchip",
        num_steps=(chip_info["X_NUM_STEPS"][1], chip_info["Y_NUM_STEPS"][1]),
        step_size=(chip_info["X_STEP_SIZE"][1], chip_info["Y_STEP_SIZE"][1]),
        num_blocks=(chip_info["X_NUM_BLOCKS"][1], chip_info["Y_NUM_BLOCKS"][1]),
        block_size=(chip_info["X_BLOCK_SIZE"][1], chip_info["Y_BLOCK_SIZE"][1]),
        start_pos=(
            chip_info["X_START"][1],
            chip_info["Y_START"][1],
            chip_info["Z_START"][1],
        ),
    )

    # Read chip map
    blocks = read_chip_map(
        chipmap,
        chip.num_blocks[0],
        chip.num_blocks[1],
    )

    # Workaround for eg. I19 Eiger which saves an increment for phi/omega in meta file.
    for ax in goniometer_axes:
        if ax.transformation_type == "rotation":
            ax.increment = 0.0

    # Calculate scan start positions on chip
    if list(blocks.values())[0] == "fullchip":
        logger.info("Full chip: all the blocks will be scanned.")
        starts = compute_goniometer(chip, full=True, ax1=scan_axes[0], ax2=scan_axes[1])
        starts = fullchip_blocks_conversion(starts, chip)
    else:
        logger.info(f"Scanning blocks: {list(blocks.keys())}.")
        starts = compute_goniometer(chip, blocks, ax1=scan_axes[0], ax2=scan_axes[1])

    # Create two temporary axes to be used for scan calculations
    axis1 = Axis(scan_axes[0], "", TransformationType.TRANSLATION, (0, 0, 0))
    axis2 = Axis(scan_axes[1], "", TransformationType.TRANSLATION, (0, 0, 0))

    # Iterate over blocks to calculate scan points
    SCAN = {axis1.name: np.array([]), axis2.name: np.array([])}
    for k, v in starts.items():
        axis1.start_pos = v[axis1.name]
        axis1.increment = chip.step_size[1] * v["direction"]
        axis1.num_steps = chip.num_steps[1]
        axis2.start_pos = v[axis2.name]
        axis2.increment = chip.step_size[0]
        axis2.num_steps = chip.num_steps[0]

        logger.debug(
            f"Current block: {k}\n"
            f"{axis1.name} start: {v[axis1.name]} \n"
            f"{axis2.name} start: {v[axis2.name]} \n"
            f"Scan direction: {v['direction']} \n"
        )

        _scan = calculate_scan_points(axis1, axis2)
        SCAN[axis1.name] = np.append(SCAN[axis1.name], np.round(_scan[axis1.name], 3))
        SCAN[axis2.name] = np.append(SCAN[axis2.name], np.round(_scan[axis2.name], 3))

    # Check the number of exposures per window
    N = int(chip_info["N_EXPOSURES"][1])
    if N > 1:
        # Repeat each position N times
        SCAN = {k: [val for val in v for _ in range(N)] for k, v in SCAN.items()}
    logger.info(f"Each position has been collected {N} times.")
    logger.info(f"Pump repeat setting: {chip_info['PUMP_REPEAT'][1]}.")
    pump_info = pump_probe.model_dump()
    pump_info["n_exposures"] = N

    return SCAN, pump_info


def run_3D_grid_scan(
    goniometer_axes: list[Axis],
    chip_info: dict[str, list],
    pump_probe: PumpProbe,
    chipmap: list[int] | None = None,
    osc_axis: str = "omega",
) -> tuple[dict]:
    """_summary_

    Args:
        goniometer_axes (list[Axis]): _description_
        chip_info (dict[str, list]): _description_
        pump_probe (PumpProbe): _description_
        chipmap (list[int], optional): _description_
        osc_axis (str, optional): _description_

    Returns:
        tuple[dict]:
            OSC: dictionary with oscillation scan axis values
            TRANSL: dictionary with grid scan values
            pump_info: updated pump probe information
    """
    logger.info("Running a 3D grid scan experiment.")

    N = int(chip_info["N_EXPOSURES"][1])

    pump_info = pump_probe.model_dump()
    pump_info["repeat"] = int(chip_info["PUMP_REPEAT"][1])
    pump_info["n_exposures"] = N
    return None, None, pump_info
