"""
Experiment definitions for SSX collections:
    - extruder
    - fixed target
    - 3D grid scan
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from ..nxs_write.NexusWriter import ScanReader
from . import PumpProbe
from .SSX_chip import Chip, compute_goniometer, read_chip_map

__all__ = ["run_extruder", "run_fixed_target", "run_3D_grid_scan"]

# Define a logger object
logger = logging.getLogger("nexgen.SSX.run_expt")


def run_extruder(
    goniometer: Dict[str, List],
    num_imgs: int,
    pump_probe: PumpProbe,
) -> Tuple[Dict]:
    """Run the goniometer computations for an extruder experiment.

    Args:
        goniometer (Dict[str, List]): Goniometer definition.
        num_imgs (int): Total number of images.
        pump_probe (PumpProbe): Pump probe parameters.

    Returns:
        Tuple[Dict]:
            goniometer: updated goniometer dictionary with actual values from the scan.
            OSC: dictionary with oscillation scan axis values.
            pump_info: updated pump probe information.
    """
    logger.info("Running an extruder experiment.")

    logger.debug("All axes are fixed, setting increments to 0.0 and starts == ends.")
    goniometer["increments"] = len(goniometer["axes"]) * [0.0]
    if goniometer["starts"] is None:
        goniometer["starts"] = len(goniometer["axes"]) * [0.0]
    goniometer["ends"] = goniometer["starts"]

    OSC, TRANSL = ScanReader(goniometer, n_images=int(num_imgs))
    del TRANSL

    pump_info = pump_probe.to_dict()

    return goniometer, OSC, pump_info


def run_fixed_target(
    goniometer: Dict[str, List],
    chip_info: Dict[str, List],
    chipmap: Path | str,
    pump_probe: PumpProbe,
    osc_axis: str = "omega",
) -> Tuple[Dict]:
    """Run the goniometer computations for a fixed-target experiment.

    Args:
        goniometer (Dict[str, List]): Goniometer definition.
        chip_info (Dict[str, List]): General information about the chip: number and size of blocks, size and step of each window, start positions, number of exposures.
        chipmap (Path | str): Path to .map file. If None is passed, assumes a fullchip.
        pump_probe (PumpProbe): Pump probe parameters.
        osc_axis (str, optional): Oscillation axis. Defaults to omega.

    Returns:
        Tuple[Dict]:
            goniometer: updated goniometer dictionary with actual values from the scan.
            OSC: dictionary with oscillation scan axis values.
            TRANSL: dictionary with grid scan values.
            pump_info: updated pump probe information.
    """
    logger.info("Running a fixed target experiment.")

    # Check that the chip dict has been passed, raise error is not
    if chip_info is None:
        logger.error("No chip_dict found.")
        raise ValueError(
            "No information about the FT chip has been passed. \
            Impossible to determine scan parameters. NeXus file won't be written."
        )

    # Define chip
    chip = Chip(
        "fastchip",
        num_steps=[chip_info["X_NUM_STEPS"][1], chip_info["Y_NUM_STEPS"][1]],
        step_size=[chip_info["X_STEP_SIZE"][1], chip_info["Y_STEP_SIZE"][1]],
        num_blocks=[chip_info["X_NUM_BLOCKS"][1], chip_info["Y_NUM_BLOCKS"][1]],
        block_size=[chip_info["X_BLOCK_SIZE"][1], chip_info["Y_BLOCK_SIZE"][1]],
        start_pos=[
            chip_info["X_START"][1],
            chip_info["Y_START"][1],
            chip_info["Z_START"][1],
        ],
    )

    # Read chip map
    blocks = read_chip_map(
        chipmap,
        chip.num_blocks[0],
        chip.num_blocks[1],
    )

    # Set step size as increment for grid scan axes and set everything else to 0
    l = len(goniometer["axes"])
    # Temporary workaround for I19 scripts which saves an increment for phi in meta file.
    goniometer["increments"] = l * [0.0]
    Yidx, Xidx = (
        goniometer["axes"].index("sam_y"),
        goniometer["axes"].index("sam_x"),
    )
    goniometer["increments"][Xidx] = chip.step_size[0]
    goniometer["increments"][Yidx] = chip.step_size[1]

    # Sanity check
    if goniometer["starts"] is not None and goniometer["starts"] != goniometer["ends"]:
        logger.debug(
            "Sanity check in case the meta file has a wrong omega/phi end value."
        )
        logger.debug(
            "In this application there is no rotation so setting end values to the same as start."
        )
        goniometer["ends"] = [s for s in goniometer["starts"]]

    # Calculate scan start/end positions on chip
    if list(blocks.values())[0] == "fullchip":
        logger.info("Full chip: all the blocks will be scanned.")
        from .SSX_chip import fullchip_blocks_conversion

        start_pos, end_pos = compute_goniometer(chip, goniometer["axes"], full=True)
        start_pos = fullchip_blocks_conversion(start_pos, chip)
        end_pos = fullchip_blocks_conversion(end_pos, chip)
    else:
        logger.info(f"Scanning blocks: {list(blocks.keys())}.")
        start_pos, end_pos = compute_goniometer(chip, goniometer["axes"], blocks=blocks)

    # Iterate over blocks to calculate scan points
    OSC = {osc_axis: np.array([])}
    TRANSL = {"sam_y": np.array([]), "sam_x": np.array([])}
    for _s, _e in zip(start_pos.items(), end_pos.items()):
        # Determine wheter it's an up or down block
        col = (
            int(_e[0]) // chip.num_blocks[0]
            if int(_e[0]) % chip.num_blocks[0] != 0
            else (int(_e[0]) // chip.num_blocks[0]) - 1
        )
        # Get the values
        if goniometer["starts"] is None:
            s = _s[1]
        else:
            s = [
                goniometer["starts"][i] if i not in [Xidx, Yidx] else _s[1][i]
                for i in range(l)
            ]
        if goniometer["ends"] is None:
            e = _e[1]
        else:
            e = [
                goniometer["ends"][i] if i not in [Xidx, Yidx] else _e[1][i]
                for i in range(l)
            ]
        goniometer["starts"] = s
        # Workaround for scanspec issue (we don't want to write the actual end of the chip)
        if col % 2 == 0:
            goniometer["ends"] = [
                end - inc for end, inc in zip(e, goniometer["increments"])
            ]
        else:
            goniometer["ends"] = [
                e[i] if i != Xidx else e[i] - goniometer["increments"][i]
                for i in range(len(e))
            ]
        logger.debug(
            "Current block: \n"
            f"Starts: {goniometer['starts']} \n"
            f"Ends: {goniometer['ends']} \n"
            f"Incs: {goniometer['increments']}"
        )
        osc, transl = ScanReader(
            goniometer,
            n_images=(
                chip.num_steps[1],
                chip.num_steps[0],
            ),
            osc_axis=osc_axis,
        )
        OSC[osc_axis] = np.append(OSC[osc_axis], osc[osc_axis])
        TRANSL["sam_y"] = np.append(TRANSL["sam_y"], np.round(transl["sam_y"], 3))
        TRANSL["sam_x"] = np.append(TRANSL["sam_x"], np.round(transl["sam_x"], 3))

    N = int(chip_info["N_EXPOSURES"][1])
    if N > 1:
        # Repeat each position N times
        OSC = {k: [val for val in v for _ in range(N)] for k, v in OSC.items()}
        TRANSL = {k: [val for val in v for _ in range(N)] for k, v in TRANSL.items()}

    logger.info(f"Each position has been collected {N} times.")
    logger.info(f"Pump repeat setting: {chip_info['PUMP_REPEAT'][1]}.")
    pump_info = pump_probe.to_dict()
    pump_info["repeat"] = int(chip_info["PUMP_REPEAT"][1])
    pump_info["n_exposures"] = N

    return goniometer, OSC, TRANSL, pump_info


def run_3D_grid_scan(
    goniometer: Dict[str, List],
    chip_info: Dict[str, List],
    chipmap: Path | str,
    pump_probe: PumpProbe,
    osc_axis: str = "omega",
) -> Tuple[Dict]:
    """_summary_

    Args:
        goniometer (Dict[str, List]): _description_
        chip_info (Dict[str, List]): _description_
        chipmap (Path | str): _description_
        pump_probe (PumpProbe): _description_
        osc_axis (str, optional): _description_

    Returns:
        Tuple[Dict]:
            goniometer: updated goniometer dictionary with actual values from the scan.
            OSC: dictionary with oscillation scan axis values
            TRANSL: dictionary with grid scan values
            pump_info: updated pump probe information
    """
    logger.info("Running a 3D grid scan experiment.")

    N = int(chip_info["N_EXPOSURES"][1])

    pump_info = pump_probe.to_dict()
    pump_info["repeat"] = int(chip_info["PUMP_REPEAT"][1])
    pump_info["n_exposures"] = N
    return None, None, None, pump_info
