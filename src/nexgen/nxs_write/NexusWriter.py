"""
Writer for NeXus format files.
"""

import h5py
import logging

import numpy as np

from pathlib import Path
from typing import List, Tuple, Union

from . import find_scan_axis, calculate_scan_range, find_number_of_images

from .data_tools import data_writer

from .NXclassWriters import (
    write_NXdata,
    write_NXinstrument,
    write_NXsample,
    write_NXsource,
    write_NXdetector,
    write_NXdetector_module,
)

from ..tools.MetaReader import overwrite_beam, overwrite_detector

writer_logger = logging.getLogger("NeXusGenerator.writer")

# General writing
def write_NXmx_nexus(
    nxsfile: h5py.File,
    datafiles: List[Path],
    goniometer,
    detector,
    module,
    source,
    beam,
    attenuator,
    timestamps: Tuple,
    coordinate_frame: str = "mcstas",
    vds: str = None,
    meta: Tuple[Path, List] = (None, None),
):
    """
    Write a new NeXus file.

    This function writes a new nexus file from the information contained in the phil scopes passed as input.
    External links to HDF5 data files.

    Args:
        nxsfile:            NeXus file to be written.
        datafiles:          List of at least 1 Path object to a HDF5 data file.
        goniometer:         Scope extract defining the goniometer geometry.
        detector:           Scope extract defining the detector and its axes.
        module:             Scope extract defining geometry and description of module.
        source:             Scope extract describing the facility.
        beam:               Scope extract defining properties of beam.
        attenuator:         Scope extract defining transmission.
        timestamps:         (start, end) tuple containing timestamps for start and end time.
        coordinate_frame:   String indicating which coordinate system is being used.
        vds:                If passed, a Virtual Dataset will also be written.
        meta:               If passed, it looks through the information contained in the _meta.h5 file and adds it to the detector_scope
    """
    # If _meta.h5 file is passed, look through it for relevant information
    if meta[0]:
        writer_logger.info("Looking through _meta.h5 file for metadata.")
        # overwrite detector, overwrite beam, get list of links for nxdetector and nxcollection
        with h5py.File(meta[0], "r") as mf:
            overwrite_beam(mf, detector.description, beam)
            link_list = overwrite_detector(mf, detector, meta[1])
    writer_logger.info("Writing NXmx NeXus file ...")
    # Find total number of images that have been written across the files.
    if len(datafiles) == 1:
        with h5py.File(datafiles[0], "r") as f:
            num_images = f["data"].shape[0]
    else:
        num_images = find_number_of_images(datafiles)

    data_type = ("images", num_images)
    writer_logger.info(f"Total number of images: {num_images}")

    # Identify scan axis
    osc_axis = find_scan_axis(goniometer.axes, goniometer.starts, goniometer.ends)

    # Compute scan_range
    idx = goniometer.axes.index(osc_axis)
    if goniometer.increments[idx] != 0.0:
        scan_range = calculate_scan_range(
            goniometer.starts[idx],
            goniometer.ends[idx],
            axis_increment=goniometer.increments[idx],
        )
    else:
        scan_range = calculate_scan_range(
            goniometer.starts[idx], goniometer.ends[idx], n_images=num_images
        )

    writer_logger.info(f"Scan axis: {osc_axis}")

    # Set default attribute
    nxsfile.attrs["default"] = "entry"

    # Start writing the NeXus tree with NXentry at the top level
    nxentry = nxsfile.create_group("entry")
    nxentry.attrs["NX_class"] = np.string_("NXentry")
    nxentry.attrs["default"] = np.string_("data")
    # create_attributes(nxentry, ("NX_class", "default"), ("NXentry", "data"))

    # Application definition: /entry/definition
    nxentry.create_dataset("definition", data=np.string_("NXmx"))

    # Call the writers
    call_writers(
        nxsfile,
        datafiles,
        coordinate_frame,
        osc_axis,
        scan_range,
        data_type,
        goniometer,
        detector,
        module,
        source,
        beam,
        attenuator,
        vds,
        meta[0],
        link_list,
    )

    # NX_DATE_TIME: /entry/start_time and /entry/end_time
    if timestamps[0] is not None:
        nxentry.create_dataset("start_time", data=np.string_(timestamps[0]))
    if timestamps[1] is not None:
        nxentry.create_dataset("end_time", data=np.string_(timestamps[1]))


def write_nexus_demo(
    nxsfile: h5py.File,
    datafiles: List[Path],
    data_type: Tuple[str, int],
    coordinate_frame: str,
    goniometer,
    detector,
    module,
    source,
    beam,
    attenuator,
    vds: str = None,
):
    """
    Write a new example NeXus format file with blank data.

    This function writes a new nexus file from the information contained in the phil scopes passed as input.
    It also writes a specified number of blank data HDF5 files.
    The nuber of these files can be passed as input parameter, if it isn't it defaults to 1.

    Args:
        nxsfile:            NeXus file to be written.
        datafiles:          List of at least 1 Path object to a HDF5 data file.
        data_type:          Tuple (str, int) indicating whether the mode is images or events (and eventually how many).
        coordinate_frame:   String indicating which coordinate system is being used.
        goniometer:         Scope extract defining the goniometer geometry.
        detector:           Scope extract defining the detector and its axes.
        module:             Scope extract defining defining geometry and description of module.
        source:             Scope extract describing the facility.
        beam:               Scope extract defining properties of beam.
        attenuator:         Scope extract defining transmission.
        vds:                If passed, a Virtual Dataset will also be written.
    """
    writer_logger.info("Writing demo ...")
    writer_logger.info(f"The data file will contain {data_type[1]} {data_type[0]}")
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
            data_type = ("images", len(scan_range))
        else:
            scan_range = calculate_scan_range(
                goniometer.starts[idx], goniometer.ends[idx], n_images=data_type[1]
            )
    elif data_type[0] == "events":
        scan_range = (goniometer.starts[idx], goniometer.ends[idx])

    writer_logger.info(f"Scan axis: {osc_axis}")
    writer_logger.info("Calling data writer ...")
    # Write data files
    data_writer(
        datafiles,
        data_type,
        image_size=detector.image_size,
        scan_range=scan_range,
    )

    # Call the writers
    call_writers(
        nxsfile,
        datafiles,
        coordinate_frame,
        osc_axis,
        scan_range,
        data_type,
        goniometer,
        detector,
        module,
        source,
        beam,
        attenuator,
        vds,
    )


# def call_writers(*args,**kwargs):
def call_writers(
    nxsfile: h5py.File,
    datafiles: List[Path],
    coordinate_frame: str,
    scan_axis: str,
    scan_range: Union[Tuple, np.ndarray],
    data_type: Tuple[str, int],
    goniometer,
    detector,
    module,
    source,
    beam,
    attenuator,
    vds: str,
    metafile: Path = None,
    link_list: List = None,
):
    """ Call the writers for the NeXus base classes."""
    logger = logging.getLogger("NeXusGenerator.writer.call")
    logger.info("Calling the writers ...")

    # NXdata: entry/data
    write_NXdata(
        nxsfile,
        datafiles,
        goniometer.__dict__,
        data_type[0],
        coordinate_frame,
        scan_range,
        scan_axis,
        vds,
    )

    # NXinstrument: entry/instrument
    write_NXinstrument(
        nxsfile,
        beam.__dict__,
        attenuator.__dict__,
        source.beamline_name,
    )

    # NXdetector: entry/instrument/detector
    write_NXdetector(
        nxsfile, detector.__dict__, coordinate_frame, data_type, metafile, link_list
    )

    # NXmodule: entry/instrument/detector/module
    write_NXdetector_module(
        nxsfile,
        module.__dict__,
        coordinate_frame,
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
        coordinate_frame,
        data_type[0],
        scan_axis,
        scan_range,
    )
