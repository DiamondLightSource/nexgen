"""Define a collection parameter model for I19-2"""

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

from pydantic import field_validator

from nexgen.beamlines.beamline_utils import GeneralParams
from nexgen.utils import get_iso_timestamp


# Useful axis definitions and parameters
class GonioAxisPosition(NamedTuple):
    """Definition of goniometer axis name, start and end position, increment.

    Fields:
        id (str): Axis name.
        start (float): Axis start position.
        increment (float): Axis increment value, only needed for the scan axis. Defaults to 0.0.
        end (float, optional): Axis end position, should only be passed for Tristan (if not passed, stills \
            will be assumed). Defaults to None.
    """

    id: str
    start: float
    inc: float = 0.0
    end: float | None = None


class DetAxisPosition(NamedTuple):
    """Definition of detector axis name and position.

    Fields:
        id (str): Axis name.
        start (float): Axis start position.
    """

    id: str
    start: float = 0.0


class DetectorName(StrEnum):
    EIGER = "eiger"
    TRISTAN = "tristan"


class CollectionParams(GeneralParams):
    """Collection parameters for beamline I19-2.

    Args:
        GeneralParams (Basemodel): General collection parameters common to \
            multiple beamlines/experiments, such as exposure time, wavelength, ...
        metafile (Path | str): Path to _meta.h5 file.
        detector_name (str): Name of the detector in use for current experiment.
        tot_num_images (int, optional): Total number of frames in a collection.
        scan_axis (str, optional): Rotation scan axis. Must be passed for Tristan.
        axes_pos (list[GonioAxisPosition], optional): list of (axis_name, start, end) values for the \
            goniometer, passed from command line. Defaults to None.
        det_pos (list[DetAxisPosition], optional): List of (axis_name, start) values for the \
            detector, passed from command line. Defaults to None.
    """

    metafile: Path
    detector_name: DetectorName
    tot_num_images: int | None = None
    scan_axis: str | None = None
    axes_pos: list[GonioAxisPosition] | None = None
    det_pos: list[DetAxisPosition] | None = None
    timestamps: tuple[str, str] = (None, None)

    @field_validator("metafile", mode="before")
    @classmethod
    def _parse_metafile(cls, metafile: str | Path):
        if isinstance(metafile, str):
            return Path(metafile)
        return metafile

    @field_validator("timestamps", mode="before")
    @classmethod
    def _parse_timestamps(cls, timestamps: Sequence[int | None]):
        start = get_iso_timestamp(timestamps[0]) if timestamps[0] else ""
        end = get_iso_timestamp(timestamps[1]) if timestamps[1] else ""
        return (start, end)
