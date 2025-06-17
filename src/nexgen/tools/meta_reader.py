"""
Tools to get the information stored inside the _meta.h5 file and overwrite the phil scope.
"""

from __future__ import annotations

import logging

import numpy as np
from numpy.typing import DTypeLike

from ..nxs_utils import Axis
from ..utils import units_of_length
from .metafile import DectrisMetafile

# TODO actually define the type for scope extract and replace Any with Union
overwrite_logger = logging.getLogger("nexgen.MetaReader")
overwrite_logger.setLevel(logging.DEBUG)


def define_vds_data_type(meta_file: DectrisMetafile) -> DTypeLike:
    """Define the data type for the VDS from the bit_depth defined in the meta file.

    Args:
        meta_file (DectrisMetafile): Handle to Dectris-shaped meta.h5 file.

    Returns:
        DTypeLike: Data type as np.uint##.
    """
    overwrite_logger.debug("Define dtype for VDS creating from bit_depth_image.")
    # meta = DectrisMetafile(meta_file)

    nbits = meta_file.get_bit_depth_image()
    overwrite_logger.debug(f"Found value for bit_depth_image: {nbits}.")
    if nbits == 32:
        return np.uint32
    elif nbits == 8:
        return np.uint8
    else:
        return np.uint16


def update_axes_from_meta(
    meta_file: DectrisMetafile,
    axes_list: list[Axis],
    osc_axis: str | None = None,
    use_config: bool = False,
):
    """Update goniometer or detector axes values from those stores in the _dectris group.

    Args:
        meta_file (DectrisMetafile): Handle to Dectris-shaped meta.h5 file.
        axes_list (list[Axis]): List of axes to look up and eventually update.
        osc_axis (str | None, optional): If passed, the number of images corresponding to the osc_axis \
            will be updated too. Defaults to None.
        use_config (bool, optional): If passed read from config dataset in meta file instead of _dectris\
            group. Defaults to False.
    """
    overwrite_logger.debug("Updating axes list with values saved to _dectris group.")
    if meta_file.hasDectrisGroup is False:
        overwrite_logger.warning(
            "No Dectris group in meta file. No values will be updated."
        )
        return

    if use_config is True and meta_file.hasConfig is True:
        config = meta_file.read_config_dset()
    else:
        config = meta_file.read_dectris_config()
    num = meta_file.get_full_number_of_images()

    for ax in axes_list:
        if f"{ax.name}_start" in config.keys():
            ax.start_pos = config[f"{ax.name}_start"]
            overwrite_logger.debug(f"Start value for axis {ax.name}: {ax.start_pos}.")
            if f"{ax.name}_increment" in config.keys():
                ax.increment = config[f"{ax.name}_increment"]
                overwrite_logger.debug(
                    f"Increment value for axis {ax.name}: {ax.increment}."
                )
        if osc_axis and ax.name == osc_axis:
            ax.num_steps = num

        if ax.name == "det_z":
            dist = units_of_length(meta_file.get_detector_distance())
            ax.start_pos = dist.to("mm").magnitude
            overwrite_logger.debug(f"Start value for axis {ax.name}: {ax.start_pos}.")
