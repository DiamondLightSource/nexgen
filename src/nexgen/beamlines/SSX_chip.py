"""
Tools to read a chip and compute the coordinates of a Serial Crystallography collection.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

# I24 chip tools


def read_chip_map(mapfile: Path, x_blocks: int, y_blocks: int) -> Dict | str:
    """
    Read the .map file for the current collection on a chip.

    Args:
        mapfile (Path): Path to .map file. If None, assumes fullchip.
        x_blocks (int): Total number of blocks in x direction in the chip.
        y_blocks (int): Total number of blocks in x direction in the chip.

    Returns:
        Dict | str: A dictionary indicating the coordinates on the chip of the scanned blocks,
                        or a string indicating that the whole chip is being scanned.
    """
    if mapfile is None:
        # Assume it's a full chip
        return "fullchip"

    with open(mapfile, "r") as f:
        chipmap = f.read()

    block_list = []
    for n, line in enumerate(chipmap.rsplit("\n")):
        if n == 64:
            break
        k = line[:2]
        v = line[-1:]
        if v == "1":
            block_list.append(k)
    if len(block_list) == x_blocks * y_blocks:
        # blocks["fullchip"] = len(block_list)
        return "fullchip"

    blocks = {}
    for b in block_list:
        x = int(b) // x_blocks if int(b) % x_blocks != 0 else (int(b) // x_blocks) - 1
        if x % 2 == 0:
            val = x * x_blocks + 1
            y = int(b) - val
        else:
            val = (x + 1) * x_blocks
            y = val - int(b)
        blocks[b] = (x, y)
    return blocks


def compute_goniometer(
    chip_dict: Dict, blocks: Dict = None, full: bool = False
) -> Tuple[Dict]:
    """
    Compute the sam_y, sam_x goniometer start and end positions for a fastchip scan.
    For this calculation, at least the number and size of blocks, as well as size ans step of each window \
    should be contained in the chip_dict.
    If full is passed, assume every block in the chip is being scanned.

    Args:
        chip_dict (Dict): General information about the chip.
        blocks (Dict, optional): Coordinates of scanned blocks. Defaults to None.
        full (bool, optional): If True, calculate start and end points for all blocks. Defaults to False.

    Returns:
        Tuple[Dict]: Start and end points for each block.
    """
    x0 = chip_dict["X_START"][1]
    y0 = chip_dict["Y_START"][1]
    starts = {}
    ends = {}

    if full is True:
        for x in range(chip_dict["X_NUM_BLOCKS"][1]):
            x_start = x0 + x * chip_dict["X_BLOCK_SIZE"][1]
            if x % 2 == 0:
                for y in range(chip_dict["Y_NUM_BLOCKS"][1]):
                    y_start = y0 + y * chip_dict["Y_BLOCK_SIZE"][1]
                    x_end = (
                        x_start
                        + chip_dict["X_NUM_STEPS"][1] * chip_dict["X_STEP_SIZE"][1]
                    )
                    y_end = (
                        y_start
                        + chip_dict["Y_NUM_STEPS"][1] * chip_dict["Y_STEP_SIZE"][1]
                    )
                    starts[(x, y)] = [0, 0, y_start, x_start]
                    ends[(x, y)] = [0, 0, y_end, x_end]
            else:
                for y in range(chip_dict["Y_NUM_BLOCKS"][1] - 1, -1, -1):
                    y_end = y0 + y * chip_dict["Y_BLOCK_SIZE"][1]
                    x_end = (
                        x_start
                        + chip_dict["X_NUM_STEPS"][1] * chip_dict["X_STEP_SIZE"][1]
                    )
                    y_start = (
                        y_end
                        + chip_dict["Y_NUM_STEPS"][1] * chip_dict["Y_STEP_SIZE"][1]
                    )
                    starts[(x, y)] = [0, 0, y_start, x_start]
                    ends[(x, y)] = [0, 0, y_end, x_end]
    else:
        for k, v in blocks.items():
            x_start = x0 + v[0] * chip_dict["X_BLOCK_SIZE"][1]
            if v[0] % 2 == 0:
                y_start = x0 + v[1] * chip_dict["Y_BLOCK_SIZE"][1]
                x_end = (
                    x_start + chip_dict["X_NUM_STEPS"][1] * chip_dict["X_STEP_SIZE"][1]
                )
                y_end = (
                    y_start + chip_dict["Y_NUM_STEPS"][1] * chip_dict["Y_STEP_SIZE"][1]
                )
            else:
                y_end = x0 + v[1] * chip_dict["Y_BLOCK_SIZE"][1]
                x_end = (
                    x_start + chip_dict["X_NUM_STEPS"][1] * chip_dict["X_STEP_SIZE"][1]
                )
                y_start = (
                    y_end + chip_dict["Y_NUM_STEPS"][1] * chip_dict["Y_STEP_SIZE"][1]
                )
            starts[k] = [0.0, 0.0, round(y_start, 3), round(x_start, 3)]
            ends[k] = [0.0, 0.0, round(y_end, 3), round(x_end, 3)]

    return starts, ends
