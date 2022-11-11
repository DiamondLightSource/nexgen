"""
Tools to read a chip and compute the coordinates of a Serial Crystallography collection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

# I24 chip tools


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

    with open(mapfile, "r") as f:
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


def compute_goniometer(
    chip: Chip,
    axes: List,
    blocks: Dict = None,
    full: bool = False,
    ax0: str = "sam_x",
    ax1: str = "sam_y",
) -> Tuple[Dict]:
    """Compute the start and end coordinates of a chip scan.

    The function returns two dictionaries - one for start and one for end positions - associating a list of axes values to each scanned block.
    All values corresponding to axes unrelated to the chip will be set automatically to 0.
    If full is True, the blocks argument will be overridden and coordinates will be calculated for every block in the chip.

    Args:
        chip (Chip): General description of the chip schematics: number and size of blocks, size and step of each window, start positions.
        axes (List): List of all the goniometer axes.
        blocks (Dict, optional): Scanned blocks. Defaults to None.
        full (bool, optional): True if all blocks have been scanned. Defaults to False.
        ax0 (str, optional): Goniometer axis corresponding to 'x' on chip. Defaults to "sam_x".
        ax1 (str, optional): Goniometer axis corresponding to 'y' on chip. Defaults to "sam_y".

    Returns:
        start, end (Tuple[Dict]): Goniometer start and end coordinates for each block.

    Raises:
        ValueError: If one or both of the axes names passed as input are not in the list og goniometer axes.
    """
    x0 = chip.start_pos[0]
    y0 = chip.start_pos[1]

    if ax0 not in axes or ax1 not in axes:
        raise ValueError(
            "Axis not found in the list of goniometer axes. Please check your input."
            f"Goniometer axes: {axes}. Looking for {ax0} and {ax1}."
        )

    num_axes = len(axes)
    idx_X = axes.index(ax0)
    idx_Y = axes.index(ax1)

    starts = {}
    ends = {}

    if full is True:
        for x in range(chip.num_blocks[0]):
            x_start = x0 + x * chip.block_size[0]
            if x % 2 == 0:
                for y in range(chip.num_blocks[1]):
                    y_start = y0 + y * chip.block_size[1]
                    x_end = x_start + chip.num_steps[0] * chip.step_size[0]
                    y_end = y_start + chip.num_steps[1] * chip.step_size[1]
                    starts[(x, y)] = [
                        x_start if i == idx_X else y_start if i == idx_Y else 0.0
                        for i in range(num_axes)
                    ]
                    ends[(x, y)] = [
                        x_end if i == idx_X else y_end if i == idx_Y else 0.0
                        for i in range(num_axes)
                    ]
            else:
                for y in range(chip.num_blocks[1] - 1, -1, -1):
                    y_end = y0 + y * chip.block_size[1]
                    x_end = x_start + chip.num_steps[0] * chip.step_size[0]
                    y_start = y_end + chip.num_steps[1] * chip.step_size[1]
                    starts[(x, y)] = [
                        x_start if i == idx_X else y_start if i == idx_Y else 0.0
                        for i in range(num_axes)
                    ]
                    ends[(x, y)] = [
                        x_end if i == idx_X else y_end if i == idx_Y else 0.0
                        for i in range(num_axes)
                    ]
    else:
        for k, v in blocks.items():
            x_start = x0 + v[0] * chip.block_size[0]
            if v[0] % 2 == 0:
                y_start = x0 + v[1] * chip.block_size[1]
                x_end = x_start + chip.num_steps[0] * chip.step_size[0]
                y_end = y_start + chip.num_steps[1] * chip.step_size[1]
            else:
                y_end = x0 + v[1] * chip.block_size[1]
                x_end = x_start + chip.num_steps[0] * chip.step_size[0]
                y_start = y_end + chip.num_steps[1] * chip.step_size[1]
            starts[k] = [
                round(x_start, 3)
                if i == idx_X
                else round(y_start, 3)
                if i == idx_Y
                else 0.0
                for i in range(num_axes)
            ]
            ends[k] = [
                round(x_end, 3)
                if i == idx_X
                else round(y_end, 3)
                if i == idx_Y
                else 0.0
                for i in range(num_axes)
            ]

    return starts, ends
