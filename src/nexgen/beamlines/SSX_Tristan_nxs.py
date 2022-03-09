"""
Create a NeXus file for serial crystallography datasets collected on I19-2 Tristan10M detector.
"""

import sys
import logging

from collections import namedtuple

# Define a logger object and a formatter
logger = logging.getLogger("NeXusGenerator.I19-2_ssx")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
# Define a stream handler
CH = logging.StreamHandler(sys.stdout)
CH.setLevel(logging.DEBUG)
CH.setFormatter(formatter)
logger.addHandler(CH)

ssx_tr_collect = namedtuple(
    "ssx_collect",
    [
        "visitpath",
        "filename",
        "tot_x",
        "beam_center",
        "detector_distance",
        "start_time",
        "stop_time",
        "exposure_time",
        "transmission",
        "wavelength",
        "pump_status",
    ],
)

# Initialize dictionaries
goniometer = {}
detector = {}
module = {}
beam = {}
attenuator = {}


def write_nxs():
    pass
