from enum import StrEnum

from numpy.typing import DTypeLike
from pydantic import BaseModel


class VdsMapping(StrEnum):
    BLOCKED = "blocked"  # default, usual one
    TILED = "tiled"  # eg. jungfrau
    STRIDED = "strided"  # Need a better name but essentially eg "every other frame"
    # INTERLEAVED = "interleaved"   # TODO


class VdsSettings(BaseModel):
    vds_dtype: DTypeLike
    vds_shape: tuple
    vds_offset: int = 0
    vds_mapping: VdsMapping = VdsMapping.BLOCKED
