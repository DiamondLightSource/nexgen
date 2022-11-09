"""
Writer for NXmx format NeXus files for Electron Diffraction.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import h5py
import numpy as np

from .. import coord2mcstas, split_arrays
from . import find_number_of_images
from .NexusWriter import ScanReader
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

logger = logging.getLogger("nexgen.ED_Writer")
logger.setLevel(logging.DEBUG)


def reframe_arrays(
    coordinate_frame: str,
    goniometer: Dict[str, Any],
    detector: Dict[str, Any],
    module: Dict[str, Any],
    ED_coord_system: Dict[str, Any],
):
    """
    Split a list of offset/vector values into arrays. If the coordinate frame is not mcstas, \
    convert the arrays using the base vectors of the ED coordinate system.

    Args:
        coordinate_frame (str): Coordinate system being used.
        goniometer (Dict[str, Any]): Goniometer geometry description.
        detector (Dict[str, Any]): Detector specific parameters and its axes.
        module (Dict[str, Any]): Geometry and description of detector module.
        ED_coord_system (Dict[str, Any]): Definition of the current coordinate frame for ED. \
            It should at least contain the convention, origin and axes information as a tuple of (depends_on, type, units, vector). \
                e.g. for X axis: {"x": (".", "translation", "mm", [1,0,0])}

    Raises:
        ValueError: When the input coordinate system name and the coordinate system convention for the vectors doesn't match.
    """
    # If the vectors are not yet split, first do that as if dealing with mcstas
    if len(goniometer["vectors"]) == 3 * len(goniometer["axes"]):
        goniometer["vectors"] = list(
            split_arrays("mcstas", goniometer["axes"], goniometer["vectors"]).values()
        )

    if len(goniometer["offsets"]) == 3 * len(goniometer["axes"]):
        goniometer["offsets"] = list(
            split_arrays("mcstas", goniometer["axes"], goniometer["offsets"]).values()
        )

    if len(detector["vectors"]) == 3 * len(detector["axes"]):
        detector["vectors"] = list(
            split_arrays("mcstas", detector["axes"], detector["vectors"]).values()
        )

    if "offsets" in module.keys() and len(module["offsets"]) == 6:
        module["offsets"] = list(
            split_arrays(
                "mcstas", ["fast_axis", "slow_axis"], module["offsets"]
            ).values()
        )

    # If the input vectors have not yet been converted to mcstas, do the conversion
    if coordinate_frame != "mcstas":
        logger.info("Input coordinate frame is not mcstas, vectors will be converted.")
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
    """
    Write a new NXmx format-like NeXus file for Electron Diffraction data.
    This function performs a few checks on the coordinate frame of the input vectors \
    and then calls the writers for the relevant NeXus base classes.

    Args:
        nxsfile (h5py.File): Handle to NeXus file to be written.
        datafiles (List[Path  |  str]): List of at least 1 Path object to a HDF5 data file.
        goniometer (Dict[str, Any]): Goniometer geometry description.
        detector (Dict[str, Any]): Detector specific parameters and its axes.
        module (Dict[str, Any]): Geometry and description of detector module.
        source (Dict[str, Any]): Facility information.
        beam (Dict[str, Any]): Beam properties.
        ED_coord_system (Dict[str, Any]): Definition of the current coordinate frame for ED. \
            It should at least contain the convention, origin and base vectors.
        coordinate_frame (str, optional): Coordinate system being used. Defaults to "mcstas".
        n_images (int, optional): _description_. Defaults to None.
        timestamps (List | Tuple, optional): Start and end time of the collection, if known. \
            Preferably passed as datetime.datetime. Defaults to None.
        notes (Dict[str, Any], optional): Any useful information/comment about the collection. \
            The keys of the dictionaries will be the dataset names and the values the data. Defaults to None.
    """
    logger.info("Call the NXclass writers for Electron Diffraction data.")

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

    # Define entry_key if dealing with singla detector
    data_entry_key = (
        "/entry/data/data" if "SINGLA" in detector["description"].upper() else "data"
    )

    # If n_images is not passed, calculate it from data files
    if not n_images:
        n_images = find_number_of_images(datafiles, data_entry_key)
        logger.info(f"Total number of images: {n_images}.")

    if goniometer["ends"] is None:
        logger.info(
            "Goniometer end position has not been passed. The value for the rotation axis will be calculated from the number of images."
        )
        ax_idx = [
            goniometer["increments"].index(i)
            for i in goniometer["increments"]
            if i != 0
        ][0]
        end = goniometer["starts"][ax_idx] + goniometer["increments"][ax_idx] * n_images
        goniometer["ends"] = [
            end if i == ax_idx else 0.0 for i in range(len(goniometer["axes"]))
        ]
        logger.info(f"Goniometer end positions set to {goniometer['ends']}")

    # Define data_type
    data_type = ("images", n_images)

    # Calculate scan
    OSC, _ = ScanReader(
        goniometer, n_images=n_images
    )  # No grid scan, can be added if needed at later time
    logger.info(f"Rotation scan axis: {list(OSC.keys())[0]}.")
    logger.info(
        f"Scan from {list(OSC.values())[0][0]} to {list(OSC.values())[0][-1]}.\n"
    )

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
        detector["image_size"],
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
