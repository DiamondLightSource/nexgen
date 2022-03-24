"""
Create a NeXus file for time-resolved collections on I19-2.
Available detectors: Tristan 10M, Eiger 2X 4M.
"""

import sys

# import json
import h5py
import glob
import logging

import numpy as np

from pathlib import Path

from collections import namedtuple
from datetime import datetime
from typing import Union, Tuple

from .I19_2_params import (
    source,
    goniometer_axes,
    tristan10M_params,
    eiger4M_params,
    dset_links,
)

from .. import (
    get_iso_timestamp,
    get_nexus_filename,
)

from ..nxs_write import (
    calculate_scan_range,
)

from ..nxs_write.NexusWriter import call_writers
from ..nxs_write.NXclassWriters import write_NXentry

from ..tools.ExtendedRequest import ExtendedRequestIO

# Define a logger object and a formatter
logger = logging.getLogger("NeXusGenerator.I19-2")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(name)s %(levelname)s %(message)s")  # %(asctime)s
CH = logging.StreamHandler(sys.stdout)
CH.setLevel(logging.DEBUG)
CH.setFormatter(formatter)
logger.addHandler(CH)

maskfile = "Tristan10M_mask_with_spec.h5"
flatfieldfile = "Tristan10M_flat_field_coeff_with_Mo_17.479keV.h5"

tr_collect = namedtuple(
    "tr_collect",
    [
        "meta_file",
        "xml_file",
        "detector_name",
        "exposure_time",
        "wavelength",
        "beam_center",  # This will have a command line call anyway because I can't call it from bash
        # "beam_pos_x",
        # "beam_pos_y",
        "start_time",
        "stop_time",
        "geometry_json",  # Define these 2 ase None
        "detector_json",
    ],
)

# Initialize dictionaries
goniometer = {}  # goniometer_axes
detector = {}  # tristan10M_params
module = {}
beam = {"flux": None}
attenuator = {}


def read_from_xml(xmlfile: Union[Path, str], detector_name: str):
    ecr = ExtendedRequestIO(xmlfile)

    # Attenuator
    attenuator["transmission"] = ecr.getTransmission()

    # Detector [2theta, det_z]
    if "tristan" in detector_name.lower():
        detector["starts"] = [0.0, ecr.getSampleDetectorDistance()]
    else:
        detector["starts"] = [ecr.getTwoTheta(), ecr.getSampleDetectorDistance()]

    # Goniometer
    osc_seq = ecr.getOscillationSequence()
    # Find scan range
    if osc_seq["range"] == 0.0:
        scan_range = (osc_seq["start"], osc_seq["start"])
        num = osc_seq["number_of_images"]
    else:
        start = osc_seq["start"]
        num = osc_seq["number_of_images"]
        stop = start + num * osc_seq["range"]
        scan_range = (start, stop)
    # Determine scan axis
    if ecr.getAxisChoice() == "omega":
        scan_axis = "omega"
        omega_pos = (*scan_range, osc_seq["range"])  # 0.0)
        phi_pos = (*2 * (ecr.getOtherAxis(),), 0.0)
    else:
        scan_axis = "phi"
        phi_pos = (*scan_range, osc_seq["range"])  # 0.0)
        omega_pos = (*2 * (ecr.getOtherAxis(),), 0.0)
    kappa_pos = (*2 * (ecr.getKappa(),), 0.0)

    pos = {
        "omega": omega_pos,
        "phi": phi_pos,
        "kappa": kappa_pos,
        "sam_x": (0.0, 0.0, 0.0),
        "sam_y": (0.0, 0.0, 0.0),
        "sam_z": (0.0, 0.0, 0.0),
    }

    return scan_axis, pos, int(num)


def tristan_writer(
    master_file: Path,
    TR: namedtuple,
    scan_axis: str,
    scan_range: Tuple[float, float],
    timestamps: Tuple[str, str] = (None, None),
):
    """
    A function to call the nexus writer for Tristan 10M detector.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (namedtuple): Parameters passed from the beamline.
        scan_axis (str): Rotation axis name.
        scan_range (Tuple[float, float]): Start and end value of rotation axis.
        timestamps (Tuple[str, str], optional): Collection start and end time. Defaults to None.
    """
    # Add mask and flatfield file to detector
    detector["pixel_mask"] = maskfile
    detector["flatfield"] = flatfieldfile
    # If these two could instead be passed, I'd be happier...

    # Get on with the writing now...
    try:
        with h5py.File(master_file, "x") as nxsfile:
            nxentry = write_NXentry(nxsfile)

            if timestamps[0]:
                nxentry.create_dataset("start_time", data=np.string_(timestamps[0]))

            call_writers(
                nxsfile,
                [TR.meta_file],
                "mcstas",
                scan_axis,  # This should be omega
                scan_range,
                (detector["mode"], None),
                goniometer,
                detector,
                module,
                source,
                beam,
                attenuator,
            )

            if timestamps[1]:
                nxentry.create_dataset("end_time", data=np.string_(timestamps[1]))
            logger.info(f"{master_file} correctly written.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )


def eiger_writer(
    master_file: Path,
    TR: namedtuple,
    scan_axis: str,
    n_frames: int,
    timestamps: Tuple[str, str] = (None, None),
):
    """
    A function to call the nexus writer for Eiger 2X 4M detector.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (namedtuple): Parameters passed from the beamline.
        scan_axis (str): Rotation axis name.
        n_frames (int): Number of images.
        timestamps (Tuple[str, str], optional): Collection start and end time. Defaults to (None, None).
    """
    # Find datafiles
    logger.info("Looking for data files ...")
    filename_template = (
        TR.meta_file.parent / TR.meta_file.name.replace("meta", f"{6*'[0-9]'}")
    ).as_posix()
    filenames = [
        Path(f).expanduser().resolve() for f in sorted(glob.glob(filename_template))
    ]
    logger.info(f"Found {len(filenames)} files in directory.")

    # Get scan range array
    logger.info("Calculating scan range...")
    scan_idx = goniometer["axes"].index(scan_axis)
    scan_range = calculate_scan_range(
        goniometer["starts"][scan_idx],
        goniometer["ends"][scan_idx],
        goniometer["increments"][scan_idx],
        n_images=n_frames,
    )

    # Get on with the writing now...
    try:
        with h5py.File(master_file, "x") as nxsfile:
            nxentry = write_NXentry(nxsfile)

            if timestamps[0]:
                nxentry.create_dataset("start_time", data=np.string_(timestamps[0]))

            call_writers(
                nxsfile,
                filenames,
                "mcstas",
                scan_axis,  # This should be omega
                scan_range,
                (detector["mode"], n_frames),
                goniometer,
                detector,
                module,
                source,
                beam,
                attenuator,
                metafile=TR.meta_file,
                link_list=dset_links,
            )

            if timestamps[1]:
                nxentry.create_dataset("end_time", data=np.string_(timestamps[1]))
            logger.info(f"{master_file} correctly written.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )


def write_nxs(**tr_params):
    """
    Gather all parameters from the beamline and call the NeXus writers.
    """
    # Get info from the beamline
    TR = tr_collect(
        meta_file=Path(tr_params["meta_file"]).expanduser().resolve(),
        xml_file=Path(tr_params["xml_file"]).expanduser().resolve(),
        detector_name=tr_params["detector_name"],
        exposure_time=tr_params["exposure_time"],
        wavelength=tr_params["wavelength"],
        beam_center=tr_params["beam_center"],
        start_time=tr_params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")  #
        if tr_params["start_time"]
        else None,  # This should be datetiem type
        stop_time=tr_params["stop_time"].strftime(
            "%Y-%m-%dT%H:%M:%S"
        )  # .strftime("%Y-%m-%dT%H:%M:%S")
        if tr_params["stop_time"]
        else None,  # idem.
        geometry_json=tr_params["geometry_json"]
        if tr_params["geometry_json"]
        else None,
        detector_json=tr_params["detector_json"]
        if tr_params["detector_json"]
        else None,
    )

    logger.info(f"{TR.detector_name} NeXus file writer.")
    logger.info(f"Current collection directory: {TR.meta_file.parent}")
    # Add some information to logger
    logger.info("Creating a NeXus file for %s ..." % TR.meta_file.name)
    # Get NeXus filename
    master_file = get_nexus_filename(TR.meta_file)
    logger.info("NeXus file will be saved as %s" % master_file)

    # Get goniometer and detector parameters
    # FIXME I mean, it works but ... TODO
    if TR.geometry_json:
        # here call json reader
        pass
    else:
        for k, v in goniometer_axes.items():
            goniometer[k] = v

    if TR.detector_json:
        # idem aedem idem
        pass
    else:
        if "tristan" in TR.detector_name.lower():
            for k, v in tristan10M_params.items():
                detector[k] = v
        else:
            for k, v in eiger4M_params.items():
                detector[k] = v

    # Read information from xml file
    scan_axis, pos, n_frames = read_from_xml(TR.xml_file, TR.detector_name)
    # n_Frames is only useful for eiger
    # pos[scan_axis][::-1] is scan range

    # Finish adding to dictionaries
    # Goniometer
    goniometer["starts"] = []
    goniometer["ends"] = []
    goniometer["increments"] = []
    for ax in goniometer["axes"]:
        goniometer["starts"].append(pos[ax][0])
        goniometer["ends"].append(pos[ax][1])
        goniometer["increments"].append(pos[ax][2])

    # Detector
    detector["exposure_time"] = TR.exposure_time
    detector["beam_center"] = TR.beam_center

    # Module
    module["fast_axis"] = detector.pop("fast_axis")
    module["slow_axis"] = detector.pop("slow_axis")
    # Set value for module_offset calculation.
    module["module_offset"] = "1"

    # Beam
    beam["wavelength"] = TR.wavelength
    beam["flux"] = None

    # Get timestamps in the correct format if they aren't already
    timestamps = (
        get_iso_timestamp(TR.start_time),
        get_iso_timestamp(TR.stop_time),
    )

    logger.info(f"Timestamps recorded: {timestamps}")

    logger.info("Goniometer information")
    logger.info(f"Scan axis is: {scan_axis}")
    for j in range(len(goniometer["axes"])):
        logger.info(
            f"Goniometer axis: {goniometer['axes'][j]} => {goniometer['starts'][j]}, {goniometer['types'][j]} on {goniometer['depends'][j]}"
        )
    logger.info("Detector information")
    logger.info(f"{detector['description']}")
    logger.info(
        f"Sensor made of {detector['sensor_material']} x {detector['sensor_thickness']}"
    )
    logger.info(
        f"Detector is a {detector['image_size']} array of {detector['pixel_size']} pixels"
    )
    for k in range(len(detector["axes"])):
        logger.info(
            f"Detector axis: {detector['axes'][k]} => {detector['starts'][k]}, {detector['types'][k]} on {detector['depends'][k]}"
        )

    logger.info(f"Recorded beam center is: {TR.beam_center}.")

    if "tristan" in TR.detector_name:
        tristan_writer(master_file, TR, scan_axis, pos[scan_axis][:-1], timestamps)
    else:
        eiger_writer(master_file, TR, scan_axis, n_frames, timestamps)


def main():
    " Call from the beamline"
    # Not the best but it should do the job
    import argparse
    from ..command_line import version_parser

    parser = argparse.ArgumentParser(description=__doc__, parents=[version_parser])
    parser.add_argument("meta_file", type=str, help="Path to _meta.h5 file")
    parser.add_argument("xml_file", type=str, help="Path to GDA generated xml file")
    parser.add_argument(
        "detector_name", type=str, help="Detector currently in use on beamline"
    )
    parser.add_argument("exp_time", type=str, help="Exposure time")
    parser.add_argument("wavelength", type=str, help="Incident beam wavelength")
    parser.add_argument("beam_center_x", type=str, help="Beam center x position")
    parser.add_argument("beam_center_y", type=str, help="Beam center y position")
    parser.add_argument(
        "--start", "--start-time", type=str, default=None, help="Collection start time"
    )
    parser.add_argument(
        "--stop", "--stop-time", type=str, default=None, help="Collection end time"
    )
    parser.add_argument(
        "--geom",
        "--geometry-json",
        type=str,
        default=None,
        help="Path to GDA generated geometry json file",
    )
    parser.add_argument(
        "--det",
        "--detector-json",
        type=str,
        default=None,
        help="Path to GDA generated detector json file",
    )
    args = parser.parse_args()

    write_nxs(
        meta_file=args.meta_file,
        xml_file=args.xml_file,
        detector_name=args.detector_name,  # "tristan",
        exposure_time=float(args.exp_time),
        wavelength=float(args.wavelength),
        beam_center=[
            float(args.beam_center_x),
            float(args.beam_center_y),
        ],  # [1590.7, 1643.7],
        start_time=datetime.strptime(args.start, "%Y-%m-%dT%H:%M:%SZ")
        if args.start
        else None,
        stop_time=datetime.strptime(args.stop, "%Y-%m-%dT%H:%M:%SZ")
        if args.stop
        else None,  # datetime.now(),
        geometry_json=args.geom if args.geom else None,
        detector_json=args.det if args.det else None,
    )


# # Example usage
# if __name__ == "__main__":

#     write_nxs(
#         meta_file=sys.argv[1],
#         xml_file=sys.argv[2],
#         detector_name=sys.argv[3],  # "tristan",
#         exposure_time=100.0,
#         wavelength=0.649,
#         beam_center=[1590.7, 1643.7],
#         start_time=datetime.now(),
#         stop_time=None,  # datetime.now(),
#         geometry_json=None,
#         detector_json=None,
#     )
