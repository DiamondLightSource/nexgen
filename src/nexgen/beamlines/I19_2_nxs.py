"""
Create a NeXus file for time-resolved collections on I19-2.
"""

import logging

# from .I19_2_params import (
#    dset_links,
#    eiger4M_params,
#    goniometer_axes,
#    source,
#    tristan10M_params,
# )

# Define a logger object
logger = logging.getLogger("nexgen.I19-2_NeXus")

# Tristan mask and flatfield files
maskfile = "Tristan10M_mask_with_spec.h5"
flatfieldfile = "Tristan10M_flat_field_coeff_with_Mo_17.479keV.h5"

# Define coordinate frame
coordinate_frame = "mcstas"

# Initialize dictionaries
goniometer = {}
detector = {}
module = {}
beam = {"flux": None}
attenuator = {}


def tristan_writer():
    pass


def eiger_writer():
    pass


def nexus_writer(**params):
    pass
