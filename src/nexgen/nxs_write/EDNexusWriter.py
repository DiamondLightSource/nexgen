"""_summary_
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import h5py
import numpy as np

from nexgen.nxs_write.NexusWriter import ScanReader

from .. import coord2mcstas, split_arrays
from . import find_number_of_images
from .NXclassWriters import (
    write_NXcoordinate_system_set,
    write_NXdata,
    write_NXdatetime,
    write_NXdetector,
    write_NXdetector_module,
    write_NXentry,
    write_NXinstrument,
    write_NXnote,
    write_NXsample,
    write_NXsource,
)

# SOmething like this ?
# ED_coord_system = {
#     "convention": "ED",
#     "origin": (0, 0, 0),
#     "x": (".", "translation", "mm", []),        # (depends, type, unit, vector)
#     "y": ("x", "translation", "mm", []),
#     "z": ("y", "translation", "mm", []),
# }


def reframe_arrays(coordinate_frame, goniometer, detector, module, ED_coord_system):
    """_summary_

    Args:
        coordinate_frame (_type_): _description_
        goniometer (_type_): _description_
        detector (_type_): _description_
        module (_type_): _description_
        ED_coord_system (_type_): _description_

    Raises:
        ValueError: _description_
    """
    # If the vectors are not yet split, first do that
    if len(goniometer["vectors"]) == 3 * len(goniometer["axes"]):
        goniometer["vectors"] = list(
            split_arrays(
                coordinate_frame, goniometer["axes"], goniometer["vectors"]
            ).values()
        )

    if len(goniometer["offsets"]) == 3 * len(goniometer["axes"]):
        goniometer["offsets"] = list(
            split_arrays(
                coordinate_frame, goniometer["axes"], goniometer["offsets"]
            ).values()
        )

    if len(detector["vectors"]) == 3 * len(detector["axes"]):
        detector["vectors"] = list(
            split_arrays(
                coordinate_frame, detector["axes"], detector["vectors"]
            ).values()
        )

    # If the input vectors have not yet been converted to mcstas, do the conversion
    if coordinate_frame != "mcstas":
        if coordinate_frame != ED_coord_system["convention"]:
            raise ValueError(
                "The input coordinate frame value doesn't match the current cordinate system convention."
                "Impossible to convert to mcstas."
            )
        mat = np.array(
            [
                ED_coord_system["x"][-1],
                ED_coord_system["y"][-1],
                ED_coord_system["z"][-1],
            ]
        )

        # Goniometer
        goniometer["vectors"] = [coord2mcstas(v, mat) for v in goniometer["vectors"]]
        goniometer["offsets"] = [coord2mcstas(v, mat) for v in goniometer["offsets"]]

        # Detector
        detector["vectors"] = [coord2mcstas(v, mat) for v in detector["vectors"]]

        # Module
        module["fast_axis"] = coord2mcstas(module["fast_axis"], mat)
        module["slow_axis"] = coord2mcstas(module["slow_axis"], mat)


# Write NeXus base classes for ED.
def ED_call_writers(
    nxsfile: h5py.File,
    datafiles: List[Path | str],
    goniometer: Dict[str, Any],
    detector: Dict[str, Any],
    module: Dict[str, Any],
    source: Dict[str, Any],
    beam: Dict[str, Any],
    ED_coord_system: Dict[str, Any],
    coordinate_frame: str = "mcstas",
    n_images: int = None,
    timestamps: List | Tuple = None,
    notes: Dict[str, Any] = None,
):
    """_summary_

    Args:
        nxsfile (h5py.File): _description_
        datafiles (List[Path  |  str]): _description_
        goniometer (Dict[str, Any]): _description_
        detector (Dict[str, Any]): _description_
        module (Dict[str, Any]): _description_
        source (Dict[str, Any]): _description_
        beam (Dict[str, Any]): _description_
        ED_coord_system (Dict[str, Any]): _description_
        coordinate_frame (str, optional): _description_. Defaults to "mcstas".
        n_images (int, optional): _description_. Defaults to None.
        timestamps (List | Tuple, optional): _description_. Defaults to None.
        notes (Dict[str, Any], optional): _description_. Defaults to None.
    """
    logger = logging.getLogger("nexgen.EDCall")
    logger.setLevel(logging.DEBUG)
    logger.info("")

    # For the moment since there's no attenuator just set to none
    attenuator = {"transmission": None}

    # Deal with vecotrs/offsets/whatever
    reframe_arrays(
        coordinate_frame,
        goniometer,
        detector,
        module,
        ED_coord_system,
    )

    # Check that filenames are paths
    if all(isinstance(f, Path) for f in datafiles) is False:
        datafiles = [Path(f).expanduser().resolve() for f in datafiles]

    # Define data_type
    data_type = ("images", n_images)

    # Define entry_key if dealing with singla detector
    data_entry_key = (
        "/entry/data/data" if "SINGLA" in detector["description"].upper() else "data"
    )

    # If n_images is not passed, calculate it from data files
    if not n_images:
        n_images = find_number_of_images(datafiles, data_entry_key)

    # Calculate scan
    OSC, _ = ScanReader(
        goniometer, n_images=n_images
    )  # No grid scan, can be added if needed at later time

    # NXentry: /entry
    write_NXentry(nxsfile)

    # NXcoordinate_system_set: /entry/coordinate_system_set
    base_vectors = {k: ED_coord_system.get(k) for k in ["x", "y", "z"]}
    write_NXcoordinate_system_set(
        nxsfile, ED_coord_system["convention"], base_vectors, ED_coord_system["origin"]
    )

    # NXdata: /entry/data
    write_NXdata(
        nxsfile, datafiles, goniometer, data_type, OSC, entry_key=data_entry_key
    )

    # NXinstrument: /entry/instrument
    write_NXinstrument(
        nxsfile,
        beam,
        attenuator,
        source["beamline_name"],
    )

    # NXdetector: /entry/instrument/detector
    write_NXdetector(
        nxsfile,
        detector,
        data_type,
    )

    # NXmodule: /entry/instrument/detector/module
    write_NXdetector_module(
        nxsfile,
        module,
        detector["image_size"],  # [::-1],
        detector["pixel_size"],
        beam_center=detector["beam_center"],
    )

    # NXsource: /entry/source
    write_NXsource(nxsfile, source)

    # NXsample: /entry/sample
    write_NXsample(
        nxsfile,
        goniometer,
        data_type,
        OSC,
    )

    # NXdatetime: /entry/start_time and /entry/stop_time
    if timestamps:
        write_NXdatetime(nxsfile, timestamps)

    # NXnote: /entry/notes
    if notes:
        write_NXnote(nxsfile, "/entry/notes", notes)
