"""
Writer for NeXus format files.
"""

import h5py

from . import find_scan_axis, calculate_scan_range
from data_tools import data_writer
from NXclassWriters import (
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
    data_type: tuple,
    coord_frame: str,
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
        data_type:      Tuple (str, int) indicating whether the mode is images or events (and eventually how many).
        coord_frame:    String indicating which coordinate system is being used.
        goniometer:     Scope extract
        detector:       Scope extract
        module:         Scope extract
        source:         Scope extract
        beam:           Scope extract
        attenuator:     Scope extract
    """
    # Identify scan axis
    osc_axis = find_scan_axis(goniometer.axes, goniometer.starts, goniometer.ends)

    # Compute scan_range
    idx = goniometer.axes.index(osc_axis)
    if data_type[0] == "images":
        if data_type[1] is None:
            scan_range = calculate_scan_range(
                goniometer.starts[idx],
                goniometer.ends[idx],
                axis_increment=goniometer.increments[idx],
            )
            num_images = len(scan_range)
        else:
            scan_range = calculate_scan_range(
                goniometer.starts[idx], goniometer.ends[idx], n_images=data_type[1]
            )
            num_images = data_type[1]
    elif data_type[0] == "events":
        scan_range = (goniometer.starts[idx], goniometer.ends[idx])

    # Write data files
    data_writer(
        datafile_list,
        data_type,
        image_size=detector.image_size,
        scan_range=scan_range,
    )

    # NXdata: entry/data
    write_NXdata(
        nxsfile,
        datafile_list,
        goniometer.__dict__,
        data_type,
        coord_frame=coord_frame,
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
    write_NXdetector(nxsfile, detector.__dict__, coord_frame, data_type, num_images)

    # NXmodule: entry/instrument/detector/module
    write_NXdetector_module(
        nxsfile,
        module.__dict__,
        coord_frame,
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
        coord_frame,
        data_type,
        osc_axis,
        scan_range=scan_range,
    )
