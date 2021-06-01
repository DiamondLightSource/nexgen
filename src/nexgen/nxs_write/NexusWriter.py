"""
Writer for NeXus format files.
"""

import h5py
import time
import datetime
import numpy as np

# from data import generate_image_data, generate_event_data
# from . import calculate_origin, split_arrays
# from .. import imgcif2mcstas, create_attributes, set_dependency
from .. import create_attributes

# NXinstrument
def write_NXinstrument(nxsfile: h5py.File, source, beam, attenuator, detector):
    # 1 - check whether file already has nxentry, if it doesn't create it
    # 2 - write nxinstrument and attributes
    # 3 - write nxattenuator
    # 4 - write nxbeam
    # 5 - write nxsource
    # 6 - call write_NXdetector
    # 7 - call write_NXpositioner
    pass


# NXsample
def write_NXsample(nxsfile: h5py.File, goniometer):
    # 1 - check whether file already has nxentry, if it doesn't create it
    # 2 - create nxsample with attributes
    # 3 - look for nxbeam in file, if there make link
    # 4 - write sample_depends_on
    # 5 - create nxtransformation
    # 6 - determine scan axis
    # 7 - try: make a link to scan axis in nxdata
    # 7 - if it doesn't exist, write here
    # 8 - write sample_ groups from goniometer (only angles)
    # 9 - write links to sample_ in transformations
    pass


# General writing (probably a temporary solution)
def write_new_nexus(
    nxsfile: h5py.File, input_params, goniometer, detector, source, beam, attenuator
):
    """
    Write a NeXus format file.

    Args:
        nxsfile:        NeXus file to be written.
        input_params:   params.input
        goniometer:
        detector:
        source:
        beam:
        attenuator:
    """
    # Record string with start_time
    start_time = datetime.fromtimestamp(time.time()).strftime("%A, %d. %B %Y %I:%M%p")

    # Set default attribute
    nxsfile.attrs["default"] = "entry"

    # Start writing the NeXus tree with NXentry at the top level
    nxentry = nxsfile.create_group("entry")
    create_attributes(nxentry, ("NX_class", "default"), ("NXentry", "data"))

    # Record string with end_time
    end_time = datetime.fromtimestamp(time.time()).strftime("%A, %d. %B %Y %I:%M%p")

    # Write /entry/start_time and /entry/end_time
    nxentry.create_dataset("start_time", data=np.string_(start_time))
    nxentry.create_dataset("end_time", data=np.string_(end_time))
