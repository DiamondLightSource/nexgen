"""
Writer for NeXus format files.
"""

# import sys
import h5py
import time
import datetime
import numpy as np

# from pathlib import Path

# from data import generate_image_data, generate_event_data
# from . import calculate_origin, split_arrays
# from .. import imgcif2mcstas, create_attributes, set_dependency
from . import find_scan_axis, calculate_scan_range
from .. import create_attributes
from nxs_write.data import data_writer
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
    datafile_list: list,
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
        datafile_list:  List of at least 1 Path object to a HDF5 data file.
        input_params:   Scope extract
        goniometer:     Scope extract
        detector:       Scope extract
        source:         Scope extract
        beam:           Scope extract
        attenuator:     Scope extract
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

    # Identify scan axis
    osc_axis = find_scan_axis(goniometer.axes, goniometer.starts, goniometer.ends)
    # Compute scan_range
    idx = goniometer.axes.index(osc_axis)
    if input_params.n_images is None:
        scan_range = calculate_scan_range(
            goniometer.starts[idx],
            goniometer.ends[idx],
            axis_increment=goniometer.increments[idx],
        )
    else:
        scan_range = calculate_scan_range(
            goniometer.starts[idx], goniometer.ends[idx], n_images=input_params.n_images
        )
    # Write data files
    data_writer(
        datafile_list,
        data_type=detector.mode,
        image_size=detector.image_size,
        scan_range=scan_range,
        n_events=input_params.n_events,
    )

    # NXdata: entry/data
    write_NXdata(
        nxsfile,
        datafile_list,
        goniometer.__dict__,
        data_type=detector.mode,
        coord_frame=input_params.coordinate_frame,
        scan_range=scan_range,
        scan_axis=osc_axis,
    )

    # NXinstrument: entry/instrument
    write_NXinstrument(
        nxsfile,
        beam.__dict__,
        attenuator.__dict__,
        detector.__dict__,
        source.beamline_name,
    )

    # NXsource: entry/source
    write_NXsource(nxsfile, source.__dict__)

    # NXsample: entry/sample

    # Record string with end_time
    end_time = datetime.fromtimestamp(time.time()).strftime("%A, %d. %B %Y %I:%M%p")

    # Write /entry/start_time and /entry/end_time
    nxentry.create_dataset("start_time", data=np.string_(start_time))
    nxentry.create_dataset("end_time", data=np.string_(end_time))
