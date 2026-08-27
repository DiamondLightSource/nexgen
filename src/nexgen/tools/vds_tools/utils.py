import logging
from enum import StrEnum
from typing import Any, TypeAlias

import h5py
import numpy as np
from numpy.typing import DTypeLike
from pydantic import BaseModel, ConfigDict

PydanticDTypeLike: TypeAlias = np.dtype[Any] | type | str | None

vds_logger = logging.getLogger("nexgen.tools.vds_tools")


class VdsMapping(StrEnum):
    BLOCKED = "blocked"  # default, usual one
    TILED = "tiled"  # eg. jungfrau
    STRIDED = "strided"  # Need a better name but essentially eg "every other frame"
    # INTERLEAVED = "interleaved"   # TODO


class VdsSettings(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    vds_dtype: PydanticDTypeLike
    vds_shape: tuple
    vds_offset: int = 0
    vds_mapping: VdsMapping = VdsMapping.BLOCKED


def find_datasets_in_file(nxdata: h5py.Group) -> list[str]:
    """
    Look for the source datasets in the NeXus file.
    Assumes that the source datasets are always h5py.ExternalLink.

    Args:
        nxdata (h5py.Group): Group where the data should be linked.

    Raises:
        KeyError: If no ExternalLinks to data are found in the group.

    Returns:
        dsets (list): The source datasets.
    """
    dsets = []
    for k in nxdata.keys():
        if isinstance(nxdata.get(k, getlink=True), h5py.ExternalLink):
            dsets.append(k)
    if not dsets:
        vds_logger.error("No extrnale link datasets found.")
        raise KeyError(
            f"No External Link datasets found in NeXus file under {nxdata.name}"
        )
    return dsets


def define_vds_dtype_from_bit_depth(bit_depth: int) -> DTypeLike:
    """Define dtype of VDS based on the passed bit depth."""
    if bit_depth == 32:
        return np.uint32
    elif bit_depth == 8:
        return np.uint8
    else:
        return np.uint16


def clean_unused_links(
    nxsfile: h5py.File,
    vds_shape: tuple | list,
    start_index: int = 0,
):
    """
    Remove links to external data not used in VDS.

    Args:
        nxsfile (h5py.File): Handle to NeXus file being written.
        vds_shape (tuple | list): Actual shape of the VDS dataset, usually defined as (num_frames, *image_size).
        start_index(int): The start point for the source data. Defaults to 0.
    """
    vds_logger.debug("Cleaning links unused in VDS ...")
    # Location of the VDS
    nxdata = nxsfile["/entry/data"]
    dataset_names = find_datasets_in_file(nxdata)
    if len(dataset_names) == 1:
        vds_logger.debug("Only one linked file, no need to remove it.")
        return
    datasets = [nxdata[name] for name in dataset_names]
    dataset_lengths = [d.shape[0] for d in datasets]
    if sum(dataset_lengths) == vds_shape[0]:
        vds_logger.debug("All links are used in VDS, no need to remove any.")
        return
    for i, _ in enumerate(datasets):
        # unlink datasets before the start of VDS
        if sum(dataset_lengths[0 : i + 1]) < start_index:
            vds_logger.debug(f"Removing {dataset_names[i]} link.")
            del nxdata[dataset_names[i]]
        # unlink datasets after the end of VDS
        if sum(dataset_lengths[0:i]) > start_index + vds_shape[0]:
            vds_logger.debug(f"Removing {dataset_names[i]} link.")
            del nxdata[dataset_names[i]]
    vds_logger.debug("Links unused in VDS removed from NeXus file.")
