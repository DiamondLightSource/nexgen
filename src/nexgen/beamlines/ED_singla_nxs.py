"""
Create a nexus file for electron diffraction collections using singla detector.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from .. import log
from ..nxs_write.NXmxWriter import EDNXmxFileWriter
from ..utils import coerce_to_path, get_iso_timestamp, get_nexus_filename
from .ED_params import ED_coord_system

logger = logging.getLogger("nexgen.EDNeXusWriter")

# Define entry_key if dealing with singla detector
SINGLA_DATA_ENTRY_KEY = "/entry/data/data"


def singla_nexus_writer(
    master_file: Path | str,
    det_distance: float,
    exp_time: float,
    ED_cs: Dict = ED_coord_system,
    datafiles: List[Path | str] = None,
    **params,
):
    """Gather all collection parameters and write the NeXus file for an electron \
    diffraction collectio using SINGLA detector.

    Args:
        master_file (Path | str): Singla master file.
        det_distance (float): Sample-detector distance, in mm.
        exp_time (float): Exposure time, in s.
        ED_cs (Dict, optional): Definition of the ED coordinate system in use. Defaults to\
            {"convention": "ED",
            "origin": (0, 0, 0),
            "x": (".", "translation", "mm", [0, 1, 0]),
            "y": ("x", "translation", "mm", [-1, 0, 0]),
            "z": ("y", "translation", "mm", [0, 0, 1]),}
        datafiles (List[Path | str], optional): List of data files. Defaults to None.

    Keyword Args:
        n_imgs (int): Total number of images in collection.
        outdir (Path | str): Directory where to save the file. Only specify if different \
            from meta_file directory.
        beam_center (List[float, float]): Beam center position, in pixels.
        wavelength (float): Wavelength of incident beam, in A.
        start_time (datetime): Experiment start time.
    """
    master_file = coerce_to_path(master_file)

    # Get NeXus filename
    nxsfile = get_nexus_filename(master_file)
    if "outdir" in list(params.keys()) and params["outdir"]:
        wdir = coerce_to_path(params["outdir"])
        nxsfile = wdir / nxsfile.name
    else:
        wdir = master_file.parent

    # Set up logging config
    logfile = wdir / "EDnxs.log"
    log.config(logfile.as_posix())

    logger.info("NeXus file writer for electron diffraction data from Singla.")
    logger.info("NeXus file will be saved as %s" % nxsfile)

    # Get start_time timestamp in ISOformat
    if "start_time" in list(params.keys()):
        start_time = get_iso_timestamp(params["start_time"])
    else:
        start_time = None
    print(start_time)

    try:
        EDFileWriter = EDNXmxFileWriter()
        print(EDFileWriter)
    except Exception as err:
        print(err)
