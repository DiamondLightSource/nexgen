"""
Create a NeXus file for serial crystallography datasets collected on I24 Eiger 2X 9M detector.
"""
import sys

# import json
import glob
import h5py
import logging

import numpy as np

from typing import List
from pathlib import Path

# from datetime import datetime
from collections import namedtuple

from .I24_Eiger_params import goniometer_axes, eiger9M_params, source

from .. import (
    get_iso_timestamp,
    get_nexus_filename,
)

from ..nxs_write import (
    calculate_scan_range,
    find_scan_axis,
)
from ..nxs_write.NexusWriter import call_writers
from ..nxs_write.NXclassWriters import write_NXentry, write_NXnote

from ..tools.MetaReader import overwrite_detector, overwrite_beam

# Define a logger object and a formatter
logger = logging.getLogger("NeXusGenerator.I24")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
# Define a stream handler
CH = logging.StreamHandler(sys.stdout)
CH.setLevel(logging.DEBUG)
CH.setFormatter(formatter)
logger.addHandler(CH)

ssx_collect = namedtuple(
    "ssx_collect",
    [
        "visitpath",
        "filename",
        "exp_type",
        "num_imgs",
        "detector_distance",
        "start_time",
        "stop_time",
        "exposure_time",
        "transmission",
        "flux",
        "pump_status",
        "pump_exp",
        "pump_delay",
    ],
)

# Initialize dictionaries
goniometer = goniometer_axes
detector = eiger9M_params
# source = source
module = {}
beam = {}
attenuator = {}

# def read_params_from_json():
#     # Paramters files path ...
#     with open(goniometer_json_path, "r") as f:
#         gonio = json.load(f)

#     with open(detector_json_path, "r") as f:
#         det = json.load(f)

#     mod = {"fast_axis": det.pop("fast_axis"), "slow_axis": det.pop("slow_axis")}
#     return gonio, det, mod


def extruder(
    master_file: Path,
    filename: List[Path],
    SSX: namedtuple,
    metafile: Path = None,  # Just in case meta is not generated for some reason
    links: List = None,
):
    """
    Write the NeXus file for extruder collections, pump-probe and not.

    Args:
        master_file (Path):     Path to the NeXus file to be written.
        filename (list):        List of paths to file.
        SSX (namedtuple):       Parameters passed from the beamline.
        metafile (Path):        Path to the _meta.h5 file. Deafults to None.
        links (List, optional): List of datasets to be linked from the meta file. Defaults to None.
    """
    goniometer["starts"] = goniometer["ends"] = goniometer["increments"] = [
        0.0,
        0.0,
        0.0,
        0.0,
    ]

    # Get timestamps in the correct format
    timestamps = (
        get_iso_timestamp(SSX.start_time),
        get_iso_timestamp(SSX.stop_time),
    )

    # Get scan range array and rotation axis
    scan_axis = find_scan_axis(
        goniometer["axes"],
        goniometer["starts"],
        goniometer["ends"],
        goniometer["types"],
    )
    scan_idx = goniometer["axes"].index(scan_axis)
    scan_range = calculate_scan_range(
        goniometer["starts"][scan_idx],
        goniometer["ends"][scan_idx],
        n_images=SSX.num_imgs,
    )

    try:
        with h5py.File(master_file, "x") as nxsfile:
            nxentry = write_NXentry(nxsfile)

            if timestamps[0]:
                nxentry.create_dataset("start_time", data=np.string_(timestamps[0]))

            call_writers(
                nxsfile,
                filename,
                "mcstas",
                scan_axis,  # This should be omega
                scan_range,
                (detector["mode"], SSX.num_imgs),
                goniometer,
                detector,
                module,
                source,
                beam,
                attenuator,
                vds="dataset",  # or None if unwanted
                metafile=metafile,
                link_list=links,
            )

            # Write pump-probe information if requested
            if SSX.pump_status == "true":
                # if SSX.pump_status is True:
                # Assuming pump_ext and pump_delay have been passed
                assert (
                    SSX.pump_exp and SSX.pump_delay
                ), "Pump exposure time and/or delay have not been recorded."
                loc = "/entry/source/notes"
                pump_info = {
                    "pump_exposure_time": SSX.pump_exp,
                    "pump_delay": SSX.pump_delay,
                }
                write_NXnote(nxsfile, loc, pump_info)

            if timestamps[1]:
                nxentry.create_dataset("end_time", data=np.string_(timestamps[1]))
            logger.info(f"{master_file} correctly written.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )


def fixed_target():
    pass


def grid_scan_3D():
    pass


def write_nxs(**ssx_params):
    """
    Gather all parameters from the beamline and call appropriate writer function for serial crystallography.
    """
    # Get info from the beamline
    SSX = ssx_collect(
        visitpath=Path(ssx_params["visitpath"]).expanduser().resolve(),
        filename=ssx_params["filename"],
        exp_type=ssx_params["exp_type"],
        num_imgs=ssx_params["num_imgs"],
        detector_distance=ssx_params["det_dist"],
        start_time=ssx_params["start_time"].strftime(
            "%Y-%m-%dT%H:%M:%S"
        ),  # should be datetiem type
        stop_time=ssx_params["stop_time"].strftime(
            "%Y-%m-%dT%H:%M:%S"
        ),  # idem. A bit of a gorilla but works.
        exposure_time=ssx_params["exp_time"],
        transmission=ssx_params["transmission"],
        flux=ssx_params["flux"],
        pump_status=ssx_params["pump_status"],
        pump_exp=ssx_params["pump_exp"],
        pump_delay=ssx_params["pump_delay"],
    )

    # Add to dictionaries
    detector["starts"] = [SSX.detector_distance]
    detector["exposure_time"] = SSX.exposure_time

    attenuator["transmission"] = SSX.transmission

    beam["flux"] = SSX.flux

    # Find metafile in directory and get info from it
    try:
        # if filename == test_##
        metafile = [
            f for f in SSX.visitpath.iterdir() if SSX.filename + "_meta" in f.as_posix()
        ][0]
        # if filename == test_##_000001
        # seq = SSX.filename.split("_")[2]
        # metafile = SSX.visitpath / (SSX.filename.replace(seq, "meta") + ".h5")
        logger.info(f"Found {metafile} in directory. Looking for metadata ...")
        # Overwrite/add to dictionary
        with h5py.File(metafile, "r") as meta:
            overwrite_beam(meta, detector["description"], beam)
            links = overwrite_detector(meta, detector)
    except IndexError:
        logger.warning(
            "No _meta.h5 file found in directory. Some metadata will be missing."
        )
        # sys.exit("Missing metadata, unable to write NeXus file. Please use command line tool.")

    module["fast_axis"] = detector.pop("fast_axis")
    module["slow_axis"] = detector.pop("slow_axis")
    # goniometer, detector, module = read_params_from_json()
    # Set value for module_offset calculation.
    module["module_offset"] = "1"

    # Find datafiles
    # if filename == test_##
    filename_template = (
        metafile.parent / metafile.name.replace("meta", f"{6*'[0-9]'}")
    ).as_posix()
    filename = [
        Path(f).expanduser().resolve() for f in sorted(glob.glob(filename_template))
    ]
    # if filename = test_##_000000
    # filename = [SSX.visitpath / (SSX.filename+".h5")]

    # Add some information to logger
    logger.info("Creating a NeXus file for %s ..." % filename)
    # Get NeXus filename
    master_file = get_nexus_filename(filename[0])
    logger.info("NeXus file will be saved as %s" % master_file)

    # Call correct function for the current experiment
    if SSX.exp_type == "extruder":
        extruder(master_file, filename, SSX, metafile, links)
    elif SSX.exp_type == "fixed_target":
        fixed_target()
    elif SSX.exp_type == "3Dgridscan":
        grid_scan_3D()


# # Example usage
# if __name__ == "__main__":
#     write_nxs(
#         visitpath=sys.argv[1],
#         filename=sys.argv[2],
#         exp_type="extruder",
#         num_imgs=100,
#         det_dist=0.5,
#         # start_time="Mon Nov 15 2021 15:59:12",
#         start_time=datetime.now(),
#         stop_time=datetime.now(),
#         # stop_time=None,
#         exp_time=0.002,
#         transmission=1.0,
#         flux=None,
#         pump_status=False,    # this is a string on the beamline
#         pump_exp=None,
#         pump_delay=None,
#     )
