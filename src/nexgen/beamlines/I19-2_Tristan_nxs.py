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
)

# from .. import (
#     get_iso_timestamp,
#     get_nexus_filename,
# )

# from ..nxs_write import (
#     calculate_scan_range,
#     find_scan_axis,
# )

from ..tools.ExtendedRequest import ExtendedRequestIO

# Define a logger object and a formatter
logger = logging.getLogger("NeXusGenerator.I19-2")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
# Define a stream handler
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
        "exposure_time",
        "wavelength",
        "beam_center",  # This will have a command line call anyway because I can't call it from bash
        # "beam_pos_x",
        # "beam_pos_y",
        "start_time",
        "end_time",
        # "pump_status",
        # "pump_exp",
        # "pump_delay",
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


def read_from_xml(xmlfile: Union[Path, str]):
    ecr = ExtendedRequestIO(xmlfile)

    # Attenuator
    attenuator["transmission"] = ecr.getTransmission()

    # Detector [2theta, det_z]
    # detector["starts"] = [ecr.getTwoTheta(), ecr.getSampleDetectorDistance()]
    detector["starts"] = [0.0, ecr.getSampleDetectorDistance()]

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
        phi_pos = (*2 * (ecr.getOtherAxis()), 0.0)
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

    print(scan_axis, pos)


def write_nxs(**tr_params):
    """
    Gather all parameters from the beamline and call the NeXus writers.
    """
    # Get info from the beamline
    TR = tr_collect(
        meta_file=Path(tr_params["meta_file"]).expanduser().resolve(),
        xml_file=Path(tr_params["xml_file"]).expanduser().resolve(),
        exposure_time=tr_params["exposure_time"],
        wavelength=tr_params["wavelength"],
        beam_center=tr_params["beam_center"],
        start_time=tr_params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if tr_params["start_time"]
        else None,  # This should be datetiem type
        stop_time=tr_params["stop_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if tr_params["start_time"]
        else None,  # idem.
        geometry_json=None,  # tr_params["geometry_json"] if tr_params["geometry_json"] else None,
        detector_json=None,  # tr_params["detector_json"] if tr_params["detector_json"] else None,
    )

    # Get goniometer and detector parameters
    # FIXME I mean, it works but ... TODO
    if TR.geometry_json:
        # here call json reader
        pass
    else:
        for k, v in goniometer_axes:
            goniometer[k] = v

    if TR.detector_json:
        # idem aedem idem
        pass
    else:
        for k, v in tristan10M_params:
            detector[k] = v
            # mah ...


# # Example usage
# if __name__ == "__main__":
#     from datetime import datetime

#     write_nxs(
#         meta_file=sys.argv[1],
#         xml_file=sys.argv[2],
#         exposure_time=100,
#         wavelength= 0.649,
#         beam_center=[1590.7, 1643.7],
#         start_time=datetime.now(),
#         stop_time=datetime.now(),
#         geometry_json=None,
#         detector_json=None,
#     )

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
