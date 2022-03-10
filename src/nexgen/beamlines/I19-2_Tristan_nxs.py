"""
Create a NeXus file for time resolved collections on I19-2 Tristan 10M detector.
"""

import sys
import json
import logging

from pathlib import Path

from collections import namedtuple
from typing import Union

# from .I19_2_params import source

# from .. import (
#     get_iso_timestamp,
#     get_nexus_filename,
# )

# from ..nxs_write import (
#     calculate_scan_range,
#     find_scan_axis,
# )

# from ..tools.ExtendedRequest import ExtendedRequestIO

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
        "geometry_json",
        "detector_json",
        "exposure_time",
        "wavelength",
        "beam_pos_x",
        "beam_pos_y",
        "start_time",
        "end_time",
        # "pump_status",
        # "pump_exp",
        # "pump_delay",
    ],
)

# Initialize dictionaries
goniometer = {}
detector = {}
module = {}
beam = {}
attenuator = {}


def read_geometry_from_json(axes_geometry: Union[Path, str]):
    """_summary_

    Args:
        axes_geometry (Union[Path, str]): _description_
    """
    # Load information from JSON file
    with open(axes_geometry, "r") as f:
        geom = json.load(f)
    print(geom)


def read_detector_params_from_json(
    detector_params: Union[Path, str],
):
    """_summary_

    Args:
        detector_params (Union[Path, str]): _description_
    """
    pass


def write_nxs():
    pass
