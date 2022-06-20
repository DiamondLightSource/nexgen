"""Utilities for writing NeXus files for beamlines at Diamond Light Source."""

from pathlib import Path
from typing import Dict, Union

# xml reader

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


def calculate_start_positions():
    pass
