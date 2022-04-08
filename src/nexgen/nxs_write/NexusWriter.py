"""
Writer for NeXus format files.
"""

import h5py
import logging

import numpy as np

from pathlib import Path
from typing import Dict, List, Tuple, Union

from . import (
    find_osc_axis,
    calculate_rotation_scan_range,
    find_grid_scan_axes,
    calculate_grid_scan_range,
    find_number_of_images,
)
from .. import units_of_time

from .NXclassWriters import (
    write_NXentry,
    write_NXdata,
    write_NXinstrument,
    write_NXsample,
    write_NXsource,
    write_NXdetector,
    write_NXdetector_module,
    write_NXdatetime,
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

    # Define a SCANS dictionary to save both rotation and eventually translation scan ranges
    SCANS = {}

    # Identify rotation scan axis
    osc_axis = find_osc_axis(
        goniometer.axes, goniometer.starts, goniometer.ends, goniometer.types
    )
    idx = goniometer.axes.index(osc_axis)

    if detector.mode == "events":
        data_type = ("events", len(datafiles))
        osc_range = (goniometer.starts[idx], goniometer.ends[idx])
    else:
        # Find total number of images that have been written across the files.
        if len(datafiles) == 1:
            with h5py.File(datafiles[0], "r") as f:
                num_images = f["data"].shape[0]
        else:
            num_images = find_number_of_images(datafiles)
        data_type = ("images", num_images)
        writer_logger.info(f"Total number of images: {num_images}")

        # Compute rotation scan_range
        if goniometer.increments[idx] != 0.0:
            osc_range = calculate_rotation_scan_range(
                goniometer.starts[idx],
                goniometer.ends[idx],
                axis_increment=goniometer.increments[idx],
            )
        else:
            osc_range = calculate_rotation_scan_range(
                goniometer.starts[idx], goniometer.ends[idx], n_images=num_images
            )

    SCANS["rotation"] = {osc_axis: osc_range}

    writer_logger.info(f"Rotatin scan axis: {osc_axis}")
    writer_logger.info(f"Scan from {osc_range[0]} tp {osc_range[-1]}.")

    # Look for a translation scan (usually on xy)
    transl_axes = find_grid_scan_axes(
        goniometer.axes, goniometer.starts, goniometer.ends, goniometer.types
    )
    # If xy scan axes are identified, add to dictionary
    if len(transl_axes) > 0:
        writer_logger.info(f"Scan along {transl_axes} axes.")
        tr_idx = [goniometer.axes.index(j) for j in transl_axes]
        transl_starts = [goniometer.starts[i] for i in tr_idx]
        transl_ends = [goniometer.ends[i] for i in tr_idx]
        transl_increments = [goniometer.increments[i] for i in tr_idx]
        for tr in range(len(transl_axes)):
            writer_logger.info(
                f"{transl_axes[tr]} scan from {transl_starts[tr]} to {transl_ends[tr]}, with a step of {transl_increments[tr]}"
            )
        # TODO decide what to do for n_images=(nx,ny) in this case...
        # Tbh, it should work without it anyway
        transl_range = calculate_grid_scan_range(
            transl_axes,
            transl_starts,
            transl_ends,
            transl_increments,
        )  # NB. leaving snaked = False for demo. TODO change at some point.
        SCANS["translation"] = transl_range

        # Just a check
        ax1 = transl_axes[0]
        assert num_images == len(
            transl_range[ax1]
        ), "The total number of images doesn't match the number of scan points, please double check the input."

    write_NXentry(nxsfile)

    # Call the writers
    call_writers(
        nxsfile,
        datafiles,
        coordinate_frame,
        SCANS,
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
        write_NXdatetime(nxsfile, (timestamps[0], None))
        # nxentry.create_dataset("start_time", data=np.string_(timestamps[0]))
    if timestamps[1] is not None:
        write_NXdatetime(nxsfile, (None, timestamps[1]))
        # nxentry.create_dataset("end_time", data=np.string_(timestamps[1]))


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
    # Define a SCANS dictionary to save both rotation and eventually translation scan ranges
    SCANS = {}

    # Identify rotation scan axis
    osc_axis = find_osc_axis(
        goniometer.axes, goniometer.starts, goniometer.ends, goniometer.types
    )
    # Look for a translation scan (usually on xy)
    transl_axes = find_grid_scan_axes(
        goniometer.axes, goniometer.starts, goniometer.ends, goniometer.types
    )

    # NB. doing this first so that if number of images is None, it can be overwritten.
    # If xy scan axes are identified, add to dictionary
    if len(transl_axes) > 0:
        writer_logger.info(f"Scan along {transl_axes} axes.")
        tr_idx = [goniometer.axes.index(j) for j in transl_axes]
        transl_starts = [goniometer.starts[i] for i in tr_idx]
        transl_ends = [goniometer.ends[i] for i in tr_idx]
        transl_increments = [goniometer.increments[i] for i in tr_idx]
        for tr in range(len(transl_axes)):
            writer_logger.info(
                f"{transl_axes[tr]} scan from {transl_starts[tr]} to {transl_ends[tr]}, with a step of {transl_increments[tr]}"
            )
        transl_range = calculate_grid_scan_range(
            transl_axes,
            transl_starts,
            transl_ends,
            transl_increments,
        )  # NB. leaving snaked = False for demo. TODO change at some point.
        SCANS["translation"] = transl_range

    # TODO FIXME the number of images should come from CLI if it's a xy scan.
    # Compute scan_range for rotation axis
    idx = goniometer.axes.index(osc_axis)
    if data_type[0] == "images":
        if data_type[1] is None and len(transl_axes) == 0:
            osc_range = calculate_rotation_scan_range(
                goniometer.starts[idx],
                goniometer.ends[idx],
                axis_increment=goniometer.increments[idx],
            )
            data_type = ("images", len(osc_range))
        elif data_type[1] is None and len(transl_axes) > 0:
            ax1 = transl_axes[0]
            num_imgs = len(transl_range[ax1])
            osc_range = calculate_rotation_scan_range(
                goniometer.starts[idx], goniometer.ends[idx], n_images=num_imgs
            )
            data_type = ("images", num_imgs)
        else:
            ax1 = transl_axes[0]
            assert data_type[1] == len(
                transl_range[ax1]
            ), "The total number of images doesn't match the number of scan points, please double check the input."
            osc_range = calculate_rotation_scan_range(
                goniometer.starts[idx], goniometer.ends[idx], n_images=data_type[1]
            )
    elif data_type[0] == "events":
        osc_range = (goniometer.starts[idx], goniometer.ends[idx])

    SCANS["rotation"] = {osc_axis: osc_range}

    writer_logger.info(f"Rotation scan axis: {osc_axis}.")
    writer_logger.info(f"Scan from {osc_range[0]} to {osc_range[-1]}.")

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
        SCANS,
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
    datafiles: List[Union[Path, str]],
    coordinate_frame: str,
    SCANS: Dict,
    data_type: Tuple[str, int],
    goniometer: Dict,
    detector: Dict,
    module: Dict,
    source: Dict,
    beam: Dict,
    attenuator: Dict,
    metafile: Union[Path, str] = None,
    link_list: List = None,
):
    """ Call the writers for the NeXus base classes."""
    logger = logging.getLogger("NeXusGenerator.writer.call")
    logger.info("Calling the writers ...")

    # Get scan details first
    osc_scan = SCANS["rotation"]
    if "translation" in SCANS.keys():
        transl_scan = SCANS["translation"]
    else:
        transl_scan = None

    # Check that filenames are paths
    if all(isinstance(f, Path) for f in datafiles) is False:
        datafiles = [Path(f).expanduser().resolve() for f in datafiles]

    if metafile:
        if type(metafile) is str:
            metafile = Path(metafile).expanduser().resolve()

    # NXdata: entry/data
    write_NXdata(
        nxsfile,
        datafiles,
        goniometer,
        data_type,
        coordinate_frame,
        osc_scan,
        transl_scan,
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
        data_type,
        osc_scan,
        transl_scan,
    )
