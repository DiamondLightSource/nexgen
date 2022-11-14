"""
Writer for NXmx format NeXus files for Electron Diffraction.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import h5py

from .. import reframe_arrays
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
        goniometer,
        detector,
        module,
        coordinate_frame,
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
            "Goniometer end position has not been passed."
            "The value for the rotation axis will be calculated from the number of images."
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
