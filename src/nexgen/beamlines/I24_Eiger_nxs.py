"""
Create a NeXus file for serial crystallography datasets collected on I24 Eiger 2X 9M detector.
"""
import sys

# import json
import h5py
import logging

from pathlib import Path

from .I24_Eiger_params import goniometer_axes, detector_params, source

# from .. import (
#     get_nexus_filename,
#     get_iso_timestamp,
# )
# from ..nxs_write.NexusWriter import call_writers

from ..tools.MetaReader import overwrite_detector, overwrite_beam

# Define a logger object and a formatter
logger = logging.getLogger("NeXusGenerator.I24")
logger.setLevel(logging.DEBUG)
# formatter = logging.Formatter("%(levelname)s %(message)s")
formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
# Define a stream handler
CH = logging.StreamHandler(sys.stdout)
CH.setLevel(logging.DEBUG)
CH.setFormatter(formatter)
logger.addHandler(CH)

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


def extruder():
    goniometer["starts"] = goniometer["ends"] = goniometer["increments"] = [
        0.0,
        0.0,
        0.0,
        0.0,
    ]
    print(goniometer)
    print(detector)
    print(module)
    print(source)


def fixed_target():
    pass


def grid_scan_3D():
    pass


def write_nxs(filename):  # (**kwargs):
    filename = Path(filename).expanduser().resolve()
    # Choose the type of experiment (for now use extruder, fixed target and 3d grid scan)
    # Info from beamline passed as argument
    # Fill dictionaries with that
    # Find metafile in directory and get info from it
    try:
        metafile = [f for f in filename.parent.iterdir() if "meta" in f.as_posix()][0]
        logger.info(f"Found {metafile} in directory. Looking for metadata ...")
    except IndexError:
        logger.warning(
            "No _meta.h5 file found in directory. Some metadata will probably be missing."
        )
    # Overwrite/add to dictionary
    with h5py.File(metafile, "r") as meta:
        overwrite_beam(meta, detector["description"], beam)
        ll = overwrite_detector(meta, detector)
    print(beam)
    print(ll)

    module["fast_axis"] = detector.pop("fast_axis")
    module["slow_axis"] = detector.pop("slow_axis")
    # goniometer, detector, module = read_params_from_json()
    # Set value for module_offset calculation.
    module["module_offset"] = "1"
    extruder()


if __name__ == "__main__":
    write_nxs(sys.argv[1])
