"""Utilities for writing NeXus files for beamlines at Diamond Light Source."""

from pathlib import Path
from typing import Dict, Tuple, Union

# I24 chip tools


def read_chip_map(mapfile: Path, x_blocks: int, y_blocks: int) -> Union[Dict, str]:
    with open(mapfile, "r") as f:
        chipmap = f.read()

    block_list = []
    for line in chipmap.rsplit("\n"):
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
    # FIXME For some combinations of windows, the order of the scans is still wrong.
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
            starts[k] = [0, 0, round(y_start, 3), round(x_start, 3)]
            ends[k] = [0, 0, round(y_end, 3), round(x_end, 3)]

    return starts, ends
