"""
Writer for NeXus format files.
"""

import h5py
import numpy as np
import time
from datetime import datetime

from . import find_scan_axis, calculate_scan_range
from .. import create_attributes
from ..nxs_write.data_tools import data_writer
from ..nxs_write.NXclassWriters import (
    write_NXdata,
    write_NXinstrument,
    write_NXsample,
    write_NXsource,
    write_NXdetector,
    write_NXdetector_module,
)

# General writing (probably a temporary solution)
def write_new_nexus(
    nxsfile: h5py.File,
    datafile_list: list,
    input_params,
    goniometer,
    detector,
    module,
    source,
    beam,
    attenuator,
):
    """
    Write a new NeXus format file.

    This function writes a new nexus file from the information contained in the phil scopes passed as input.
    It also writes a specified number of blank data HDF5 files.
    The nuber of these files can be passed as input parameter, if it isn't it defaults to 1.
    Args:
        nxsfile:        NeXus file to be written.
        datafile_list:  List of at least 1 Path object to a HDF5 data file.
        input_params:   Scope extract
        goniometer:     Scope extract
        detector:       Scope extract
        module:         Scope extract
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
        num_images = len(scan_range)
    else:
        scan_range = calculate_scan_range(
            goniometer.starts[idx], goniometer.ends[idx], n_images=input_params.n_images
        )
        num_images = input_params.n_images
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

    # NXdetector: entry/instrument/detector
    write_NXdetector(
        nxsfile, detector.__dict__, input_params.coordinate_frame, num_images
    )

    # NXmodule: entry/instrument/detector/module
    write_NXdetector_module(
        nxsfile,
        module.__dict__,
        input_params.coordinate_frame,
        detector.image_size,
        detector.pixel_size,
        beam_center=detector.beam_center,
    )

    # NXsource: entry/source
    write_NXsource(nxsfile, source.__dict__)

    # NXsample: entry/sample
    write_NXsample(
        nxsfile,
        goniometer.__dict__,
        input_params.coordinate_frame,
        detector.mode,
        osc_axis,
        scan_range=scan_range,
    )

    # Record string with end_time
    end_time = datetime.fromtimestamp(time.time()).strftime("%A, %d. %B %Y %I:%M%p")

    # Write /entry/start_time and /entry/end_time
    nxentry.create_dataset("start_time", data=np.string_(start_time))
    nxentry.create_dataset("end_time", data=np.string_(end_time))


# Write nexus file to go with existing data
# def write_nexus_for_data():
#    pass
