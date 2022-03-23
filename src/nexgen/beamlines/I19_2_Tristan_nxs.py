"""
Create a NeXus file for time resolved collections on I19-2 Tristan 10M detector.
"""

import sys

# import json
import logging

from pathlib import Path

from collections import namedtuple
from typing import Union

from .I19_2_params import (
    # source,
    goniometer_axes,
    tristan10M_params,
    eiger4M_params,
)

from .. import (
    get_iso_timestamp,
    get_nexus_filename,
)

# from ..nxs_write import (
#     calculate_scan_range,
# )

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
    else:
        start = osc_seq["start"]
        num = osc_seq["number_of_images"]
        stop = start + num * osc_seq["range"]
        scan_range = (start, stop)
    # Determine scan axis
    if ecr.getAxisChoice() == "omega":
        scan_axis = "omega"
        omega_pos = (*scan_range, 0.0)
        phi_pos = (*2 * (ecr.getOtherAxis(),), 0.0)
    else:
        scan_axis = "phi"
        phi_pos = (*scan_range, 0.0)
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

    return scan_axis, pos


def tristan_writer():
    pass


def eiger_writer():
    pass


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
        start_time=tr_params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if tr_params["start_time"]
        else None,  # This should be datetiem type
        stop_time=tr_params["stop_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if tr_params["stop_time"]
        else None,  # idem.
        geometry_json=tr_params["geometry_json"]
        if tr_params["geometry_json"]
        else None,
        detector_json=tr_params["detector_json"]
        if tr_params["detector_json"]
        else None,
    )

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
    scan_axis, pos = read_from_xml(TR.xml_file, TR.detector_name)
    print(scan_axis)
    print(pos[scan_axis][:-1])  # this is scan range

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

    # Get timestamps in the correct format
    timestamps = (
        get_iso_timestamp(TR.start_time),
        get_iso_timestamp(TR.stop_time),
    )
    print(timestamps)

    logger.info("Goniometer information")
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


# Example usage
if __name__ == "__main__":
    from datetime import datetime

    write_nxs(
        meta_file=sys.argv[1],
        xml_file=sys.argv[2],
        detector_name=sys.argv[3],  # "tristan",
        exposure_time=100,
        wavelength=0.649,
        beam_center=[1590.7, 1643.7],
        start_time=datetime.now(),
        stop_time=datetime.now(),
        geometry_json=None,
        detector_json=None,
    )

# TODO separated from this make some sort of json2params tool (see jupyter notebook)
# def read_geometry_from_json(axes_geometry: Union[Path, str]):
#     """_summary_

#     Args:
#         axes_geometry (Union[Path, str]): _description_
#     """
#     # Load information from JSON file
#     with open(axes_geometry, "r") as f:
#         geom = json.load(f)
#     print(geom)


# def read_detector_params_from_json(
#     detector_params: Union[Path, str],
# ):
#     """_summary_

#     Args:
#         detector_params (Union[Path, str]): _description_
#     """
#     pass
