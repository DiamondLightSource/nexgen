from enum import StrEnum
from typing import Any, TypeAlias

import h5py
import numpy as np
from numpy.typing import DTypeLike
from pydantic import BaseModel, ConfigDict

PydanticDTypeLike: TypeAlias = np.dtype[Any] | type | str | None


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
