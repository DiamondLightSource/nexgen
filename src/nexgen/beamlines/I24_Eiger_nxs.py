"""
Create a NeXus file for serial crystallography datasets collected on I24 Eiger 2X 9M detector.
"""
import sys

# import json
import h5py
import logging

from typing import List
from pathlib import Path
from collections import namedtuple

from .I24_Eiger_params import goniometer_axes, detector_params, source

from .. import (
    get_iso_timestamp,
    get_nexus_filename,
)

from ..nxs_write import create_attributes
from ..nxs_write.NexusWriter import call_writers

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
detector = detector_params
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


def extruder(master_file: Path, metafile: Path, SSX: namedtuple, links: List = None):
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

    try:
        with h5py.File(master_file, "x") as nxsfile:
            # TODO FIXME actually get this to call write_NXmx ... easier once all the functions are fixed
            # Set default attribute
            nxsfile.attrs["default"] = "entry"

            # Start writing the NeXus tree with NXentry at the top level
            nxentry = nxsfile.create_group("entry")
            create_attributes(nxentry, ("NX_class", "default"), ("NXentry", "data"))

            if timestamps[0]:
                nxentry.create_dataset("start_time", data=timestamps[0])

            call_writers(
                nxsfile,
                [SSX.filename],
                "mcstas",
                "omega",
                (
                    0.0,
                ),  # FIXME this should be an array of 0s as long as number of images... but I need to fixe the function.
                (detector["mode"], SSX.num_imgs),
                goniometer,
                detector,
                module,
                source,
                beam,
                attenuator,
                metafile=metafile,
                link_list=links,
            )
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
    # Get info from the beamline
    SSX = ssx_collect(
        filename=Path(ssx_params["filename"])
        .expanduser()
        .resolve(),  # If needed, fix in the future for multiple files
        exp_type=ssx_params["exp_type"],
        num_imgs=ssx_params["num_imgs"],
        detector_distance=ssx_params["det_dist"],
        start_time=ssx_params["start_time"],
        stop_time=ssx_params["stop_time"],
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

    # Add some information to logger
    logger.info("Creating a NeXus file for %s ..." % SSX.filename)
    # Get NeXus filename
    master_file = get_nexus_filename(SSX.filename)
    logger.info("NeXus file will be saved as %s" % master_file)
    # Find metafile in directory and get info from it
    try:
        metafile = [
            f for f in SSX.filename.parent.iterdir() if "meta.h5" in f.as_posix()
        ][0]
        logger.info(f"Found {metafile} in directory. Looking for metadata ...")
    except IndexError:
        logger.warning(
            "No _meta.h5 file found in directory. Some metadata will probably be missing."
        )
    # Overwrite/add to dictionary
    with h5py.File(metafile, "r") as meta:
        overwrite_beam(meta, detector["description"], beam)
        links = overwrite_detector(meta, detector)

    module["fast_axis"] = detector.pop("fast_axis")
    module["slow_axis"] = detector.pop("slow_axis")
    # goniometer, detector, module = read_params_from_json()
    # Set value for module_offset calculation.
    module["module_offset"] = "1"

    # Call correct function for the current experiment
    if SSX.exp_type == "extruder":
        extruder(master_file, metafile, SSX, links)
    elif SSX.exp_type == "fixed_target":
        fixed_target()
    elif SSX.exp_type == "3Dgridscan":
        grid_scan_3D()


if __name__ == "__main__":
    write_nxs(
        filename=sys.argv[1],
        exp_type="extruder",
        num_imgs=100,
        det_dist=0.5,
        start_time="Mon Nov 15 2021 15:59:12",
        stop_time=None,
        exp_time=0.002,
        transmission=1.0,
        flux=None,
        pump_status=False,
        pump_exp=None,
        pump_delay=None,
    )
