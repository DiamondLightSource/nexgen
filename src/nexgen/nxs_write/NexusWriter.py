"""
Writer for NeXus format files.
"""

import h5py
import logging

import numpy as np

from pathlib import Path
from typing import Dict, List, Tuple, Union

from . import find_scan_axis, calculate_scan_range, find_number_of_images
from .. import units_of_time

from .NXclassWriters import (
    write_NXentry,
    write_NXdata,
    write_NXinstrument,
    write_NXsample,
    write_NXsource,
    write_NXdetector,
    write_NXdetector_module,
)

from ..tools.MetaReader import overwrite_beam, overwrite_detector
from ..tools.DataWriter import generate_event_files, generate_image_files
from ..tools.VDS_tools import image_vds_writer, vds_file_writer

writer_logger = logging.getLogger("NeXusGenerator.writer")

# General writing
def write_nexus(
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
        meta:               (path, list) tuple containing the path to the meta file and eventualy the fields to be skipped.
                            If passed, it looks through the information contained in the _meta.h5 file and adds it to the detector_scope
    """
    # If _meta.h5 file is passed, look through it for relevant information
    if meta[0]:
        writer_logger.info("Looking through _meta.h5 file for metadata.")
        # overwrite detector, overwrite beam, get list of links for nxdetector and nxcollection
        with h5py.File(meta[0], "r") as mf:
            overwrite_beam(mf, detector.description, beam)
            link_list = overwrite_detector(mf, detector, meta[1])
    else:
        link_list = None
    writer_logger.info("Writing NXmx NeXus file ...")

    # Identify scan axis
    osc_axis = find_scan_axis(
        goniometer.axes, goniometer.starts, goniometer.ends, goniometer.types
    )
    idx = goniometer.axes.index(osc_axis)

    if detector.mode == "events":
        data_type = ("events", len(datafiles))
        scan_range = (goniometer.starts[idx], goniometer.ends[idx])
    else:
        # Find total number of images that have been written across the files.
        if len(datafiles) == 1:
            with h5py.File(datafiles[0], "r") as f:
                num_images = f["data"].shape[0]
        else:
            num_images = find_number_of_images(datafiles)
        data_type = ("images", num_images)
        writer_logger.info(f"Total number of images: {num_images}")

        # Compute scan_range
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
    writer_logger.info(f"Scan from {scan_range[0]} tp {scan_range[-1]}.")

    nxentry = write_NXentry(nxsfile)

    # Call the writers
    call_writers(
        nxsfile,
        datafiles,
        coordinate_frame,
        osc_axis,
        scan_range,
        data_type,
        goniometer.__dict__,
        detector.__dict__,
        module.__dict__,
        source.__dict__,
        beam.__dict__,
        attenuator.__dict__,
        meta[0],
        link_list,
    )

    # Write VDS
    if data_type[0] == "images" and vds == "dataset":
        writer_logger.info("Calling VDS writer ...")
        image_vds_writer(nxsfile, (data_type[1], *detector.image_size))
    elif data_type[0] == "images" and vds == "file":
        writer_logger.info(
            "Calling VDS writer to write a Virtual Dataset file and relative link."
        )
        vds_file_writer(nxsfile, datafiles, (data_type[1], *detector.image_size))
    else:
        writer_logger.info("VDS won't be written.")

    # NX_DATE_TIME: /entry/start_time and /entry/end_time
    if timestamps[0] is not None:
        nxentry.create_dataset("start_time", data=np.string_(timestamps[0]))
    if timestamps[1] is not None:
        nxentry.create_dataset("end_time", data=np.string_(timestamps[1]))


def write_nexus_demo(
    nxsfile: h5py.File,
    datafile_template: str,
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
    writer_logger.info("Writing NXmx demo ...")
    writer_logger.info(f"The data file will contain {data_type[1]} {data_type[0]}")
    # Identify scan axis
    osc_axis = find_scan_axis(
        goniometer.axes, goniometer.starts, goniometer.ends, goniometer.types
    )

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

    writer_logger.info(f"Scan axis: {osc_axis}.")
    writer_logger.info(f"Scan from {scan_range[0]} to {scan_range[-1]}.")

    # Figure out how many files will need to be written
    writer_logger.info("Calculating number of files to write ...")
    if data_type[0] == "events":
        # Determine the number of files. Write one file per module.
        # FIXME Either a 10M or a 2M, no other possibilities at this moment.
        n_files = 10 if "10M" in detector.description.upper() else 2
    else:
        # The maximum number of images being written each dataset is 1000
        if data_type[1] <= 1000:
            n_files = 1
        else:
            n_files = int(np.ceil(data_type[1] / 1000))

    writer_logger.info("%d file(s) containing blank data to be written." % n_files)

    # Get datafile list
    datafiles = [
        Path(datafile_template % (n + 1)).expanduser().resolve() for n in range(n_files)
    ]

    writer_logger.info("Calling data writer ...")
    # Write data files
    if data_type[0] == "images":
        generate_image_files(
            datafiles, detector.image_size, detector.description, data_type[1]
        )
    else:
        exp_time = units_of_time(detector.exposure_time)
        generate_event_files(
            datafiles, data_type[1], detector.description, exp_time.magnitude
        )

    write_NXentry(nxsfile)

    # Call the writers
    call_writers(
        nxsfile,
        datafiles,
        coordinate_frame,
        osc_axis,
        scan_range,
        data_type,
        goniometer.__dict__,
        detector.__dict__,
        module.__dict__,
        source.__dict__,
        beam.__dict__,
        attenuator.__dict__,
    )

    # Write VDS
    if data_type[0] == "images" and vds == "dataset":
        writer_logger.info(
            "Calling VDS writer to write a Virtual Dataset under /entry/data/data"
        )
        image_vds_writer(nxsfile, (data_type[1], *detector.image_size))
    elif data_type[0] == "images" and vds == "file":
        writer_logger.info(
            "Calling VDS writer to write a Virtual Dataset file and relative link."
        )
        vds_file_writer(nxsfile, datafiles, (data_type[1], *detector.image_size))
    else:
        writer_logger.info("VDS won't be written.")


# def call_writers(*args,**kwargs):
def call_writers(
    nxsfile: h5py.File,
    datafiles: List[Path],
    coordinate_frame: str,
    scan_axis: str,
    scan_range: Union[Tuple, np.ndarray],
    data_type: Tuple[str, int],
    goniometer: Dict,
    detector: Dict,
    module: Dict,
    source: Dict,
    beam: Dict,
    attenuator: Dict,
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
        goniometer,
        data_type[0],
        coordinate_frame,
        scan_range,
        scan_axis,
    )

    # NXinstrument: entry/instrument
    write_NXinstrument(
        nxsfile,
        beam,
        attenuator,
        source["beamline_name"],
    )

    # NXdetector: entry/instrument/detector
    write_NXdetector(
        nxsfile,
        detector,
        coordinate_frame,
        data_type,
        metafile,
        link_list,
    )

    # NXmodule: entry/instrument/detector/module
    write_NXdetector_module(
        nxsfile,
        module,
        coordinate_frame,
        detector["image_size"][::-1],
        detector["pixel_size"],
        beam_center=detector["beam_center"],
    )

    # NXsource: entry/source
    write_NXsource(nxsfile, source)

    # NXsample: entry/sample
    write_NXsample(
        nxsfile,
        goniometer,
        coordinate_frame,
        data_type[0],
        scan_axis,
        scan_range,
    )
