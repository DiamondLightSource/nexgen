"""
Create a NeXus file for time resolved collections on I19-2 Tristan 10M detector.
"""

import sys

# import json
import logging

# from pathlib import Path

from collections import namedtuple

# from .. import (
#     get_iso_timestamp,
#     get_nexus_filename,
# )

# from ..nxs_write import (
#     calculate_scan_range,
#     find_scan_axis,
# )

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
    [],
)

# Initialize dictionaries
goniometer = {}
detector = {}
module = {}
beam = {}
attenuator = {}


def read_geometry_from_json():
    pass


def read_detector_params_from_json():
    pass


def write_nxs():
    pass
