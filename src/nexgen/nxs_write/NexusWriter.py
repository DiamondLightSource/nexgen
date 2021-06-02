"""
Writer for NeXus format files.
"""

import sys
import h5py
import time
import datetime
import numpy as np
from pathlib import Path

# from data import generate_image_data, generate_event_data
# from . import calculate_origin, split_arrays
# from .. import imgcif2mcstas, create_attributes, set_dependency
from . import find_scan_axis
from .. import create_attributes
from nxs_write.NXclassWriters import (
    write_NXdata,
    write_NXinstrument,
    # write_NXsample,
    write_NXsource,
    # write_NXdetector,
    # write_NXmodule,
)

# General writing (probably a temporary solution)
def write_new_nexus(
    nxsfile: h5py.File,
    datafile: Path,
    input_params,
    goniometer,
    detector,
    source,
    beam,
    attenuator,
):
    """
    Write a new NeXus format file.

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

    # Application definition: entry/definition
    nxentry.create_dataset("definition", data=np.string_(input_params.definition))

    # NXdata: entry/data
    # Identify scan axis
    osc_axis = find_scan_axis(goniometer.axes, goniometer.starts, goniometer.ends)
    if detector.mode == "images":
        write_NXdata(
            nxsfile,
            datafile,
            goniometer,
            image_size=detector.image_size,
            scan_axis=osc_axis,
            N=input_params.n_images,
        )
    elif detector.mode == "events":
        write_NXdata(
            nxsfile,
            datafile,
            goniometer,
            data_type="events",
            image_size=detector.image_size,
            scan_axis=osc_axis,
            N=input_params.n_events,
        )
    else:
        sys.exit("Please pass a correct data_type (images or events)")

    # NXinstrument: entry/instrument
    write_NXinstrument(nxsfile, beam, attenuator, detector, source.beamline_name)

    # NXsource: entry/source
    write_NXsource(nxsfile, source)
    # NXsample: entry/sample

    # Record string with end_time
    end_time = datetime.fromtimestamp(time.time()).strftime("%A, %d. %B %Y %I:%M%p")

    # Write /entry/start_time and /entry/end_time
    nxentry.create_dataset("start_time", data=np.string_(start_time))
    nxentry.create_dataset("end_time", data=np.string_(end_time))
