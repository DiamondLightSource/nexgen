"""
Tools to read a chip and compute the coordinates of a Serial Crystallography collection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..nxs_utils.ScanUtils import ScanDirection

# I24 chip tools

CHIP_DICT_DEFAULT = {
    "X_NUM_STEPS": [0, 20],
    "Y_NUM_STEPS": [0, 20],
    "X_STEP_SIZE": [0, 0.125],
    "Y_STEP_SIZE": [0, 0.125],
    "X_START": [0, 0],
    "Y_START": [0, 0],
    "Z_START": [0, 0],
    "X_NUM_BLOCKS": [0, 8],
    "Y_NUM_BLOCKS": [0, 8],
    "X_BLOCK_SIZE": [0, 3.175],
    "Y_BLOCK_SIZE": [0, 3.175],
    "N_EXPOSURES": [0, 1],
    "PUMP_REPEAT": [0, 0],
}


@dataclass
class Chip:
    """
    Define a fixed target chip.

    Args:
        name (str): Description of the chip.
        num_steps (List[int] | Tuple[int]): Number of windows in each block.
        step_size (List[float] | Tuple[float]): Size of each window (distance between the centers in x and y direction).
        num_blocks (List[int] | Tuple[int]): Total number of blocks in the chip.
        block_size (List[int] | Tuple[int]): Size of each block.
        start_pos (List[float]): Start coordinates (x,y,z)
    """

    name: str

    num_steps: List[int, int] | Tuple[int, int]
    step_size: List[float, float] | Tuple[float, float]
    num_blocks: List[int, int] | Tuple[int, int]
    block_size: List[float, float] | Tuple[float, float]

    start_pos: List[float, float, float] = field(default_factory=[0.0, 0.0, 0.0])

    def tot_blocks(self) -> int:
        return self.num_blocks[0] * self.num_blocks[1]

    def tot_windows_per_block(self) -> int:
        return self.num_steps[0] * self.num_steps[1]

    def window_size(self) -> Tuple[float]:
        return (
            self.num_steps[0] * self.step_size[0],
            self.num_steps[1] * self.step_size[1],
        )

    def chip_size(self) -> Tuple[float]:
        return (
            self.num_blocks[0] * self.block_size[0],
            self.num_blocks[1] * self.block_size[1],
        )


def fullchip_conversion_table(chip: Chip) -> Dict:
    """Associate block coordinates to block number for a full chip.

    Args:
        chip (Chip): General description of the chip.

    Returns:
        Dict: Conversion table, keys are block numbers, values are coordinates.
    """
    coords = []
    table = {}
    for i in range(chip.num_blocks[0]):
        if i % 2 == 0:
            for j in range(chip.num_blocks[1]):
                coords.append((i, j))
        else:
            for j in range(chip.num_blocks[1] - 1, -1, -1):
                coords.append((i, j))
    for k, v in zip(range(1, chip.tot_blocks() + 1), coords):
        table[f"%0{2}d" % k] = v
    return table


def read_chip_map(mapfile: Path | str, x_blocks: int, y_blocks: int) -> Dict:
    """
    Read the .map file for the current collection on a chip.

    Args:
        mapfile (Path | str): Path to .map file. If None, assumes fullchip.
        x_blocks (int): Total number of blocks in x direction in the chip.
        y_blocks (int): Total number of blocks in y direction in the chip.

    Returns:
        Dict: A dictionary whose values indicate either the coordinates on the chip \
            of the scanned blocks, or a string indicating that the whole chip is being scanned.
    """
    if mapfile is None:
        # Assume it's a full chip
        return {"all": "fullchip"}

    with open(mapfile) as f:
        chipmap = f.read()

    block_list = []
    max_num_blocks = x_blocks * y_blocks
    for n, line in enumerate(chipmap.rsplit("\n")):
        if n == max_num_blocks:
            break
        k = line[:2]
        v = line[-1:]
        if v == "1":
            block_list.append(k)
    if len(block_list) == max_num_blocks:
        # blocks["fullchip"] = len(block_list)
        return {"all": "fullchip"}

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


def fullchip_blocks_conversion(blocks: Dict[Tuple, Any], chip: Chip) -> Dict:
    new_blocks = {}
    table = fullchip_conversion_table(chip)
    for kt, vt in table.items():
        for kb, vb in blocks.items():
            if kb == vt:
                new_blocks[kt] = vb
    return new_blocks


def compute_goniometer(
    chip: Chip,
    blocks: Dict | None = None,
    full: bool = False,
    ax1: str = "sam_y",
    ax2: str = "sam_x",
) -> Dict[Dict[str | Tuple, float | int]]:
    """Compute the start coordinates of each block in a chip scan.

    The function returns a dictionary associating a list of axes start values \
    and a scan direction to each scanned block.
    If full is True, the blocks argument will be overridden and coordinates will be \
    calculated for every block in the chip.

    Args:
        chip (Chip): General description of the chip schematics: number and size of blocks, \
            size and step of each window, start positions.
        blocks (Dict | None, optional): Scanned blocks. Defaults to None.
        full (bool, optional): True if all blocks have been scanned. Defaults to False.
        ax1 (str, optional): Axis name corrsponding to slow varying axis. Defaults to "sam_y".
        ax2 (str, optional): Axis name corrsponding to fast varying axis. Defaults to "sam_x".

    Returns:
        Dict[Dict[str | Tuple, float | int]]: Axes start coordinates and scan direction of each block. \
            eg. \
                {
                    '01'/(0,0): {
                        'ax1': 0.0,
                        'ax2': 0.0,
                        'direction': 1,
                    }
                }
    """
    x0 = chip.start_pos[0]
    y0 = chip.start_pos[1]

    axes_starts = {}

    if full is True:
        for x in range(chip.num_blocks[0]):
            x_start = x0 + x * chip.block_size[0]
            if x % 2 == 0:
                for y in range(chip.num_blocks[1]):
                    sd = ScanDirection.POSITIVE
                    y_start = y0 + y * chip.block_size[1]
                    axes_starts[(x, y)] = {
                        ax1: round(y_start, 3),
                        ax2: round(x_start, 3),
                        "direction": sd.value,
                    }
            else:
                for y in range(chip.num_blocks[1] - 1, -1, -1):
                    sd = ScanDirection.NEGATIVE
                    y_end = y0 + y * chip.block_size[1]
                    y_start = y_end + (chip.num_steps[1] - 1) * chip.step_size[1]
                    axes_starts[(x, y)] = {
                        ax1: round(y_start, 3),
                        ax2: round(x_start, 3),
                        "direction": sd.value,
                    }
    else:
        for k, v in blocks.items():
            x_start = x0 + v[0] * chip.block_size[0]
            if v[0] % 2 == 0:
                sd = ScanDirection.POSITIVE
                y_start = y0 + v[1] * chip.block_size[1]
            else:
                sd = ScanDirection.NEGATIVE
                y_end = y0 + v[1] * chip.block_size[1]
                y_start = y_end + (chip.num_steps[1] - 1) * (chip.step_size[1])
            axes_starts[k] = {
                ax1: round(y_start, 3),
                ax2: round(x_start, 3),
                "direction": sd.value,
            }

    return axes_starts
