"""
Create a NeXus file for time-resolved collections on I19-2.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, NamedTuple, Optional

import h5py
import numpy as np
from pydantic import field_validator

from nexgen.utils import get_iso_timestamp

from .. import log
from ..nxs_utils import (
    Attenuator,
    Beam,
    Detector,
    EigerDetector,
    Goniometer,
    Source,
    TristanDetector,
)
from ..nxs_utils.scan_utils import calculate_scan_points, identify_osc_axis
from ..nxs_write.nxmx_writer import EventNXmxFileWriter, NXmxFileWriter
from ..tools.meta_reader import define_vds_data_type, update_axes_from_meta
from ..tools.metafile import DectrisMetafile
from .beamline_utils import GeneralParams, collection_summary_log
from .I19_2_params import I19_2Eiger, I19_2Tristan

# Define a logger object
logger = logging.getLogger("nexgen.I19-2_NeXus")


# Useful axis definitions and parameters
class GonioAxisPosition(NamedTuple):
    """Definition of goniometer axis name, start and end position, increment.

    Fields:
        id (str): Axis name.
        start (float): Axis start position.
        increment (float): Axis increment value, only needed for the scan axis. Defaults to 0.0.
        end (float, optional): Axis end position, should only be passed for Tristan (if not passed, stills \
            will be assumed). Defaults to None.
    """

    id: str
    start: float
    inc: float = 0.0
    end: float | None = None


class DetAxisPosition(NamedTuple):
    """Definition of detector axis name and position.

    Fields:
        id (str): Axis name.
        start (float): Axis start position.
    """

    id: str
    start: float = 0.0


class DetectorName(StrEnum):
    EIGER = "eiger"
    TRISTAN = "tristan"


class CollectionParams(GeneralParams):
    """Collection parameters for beamline I19-2.

    Args:
        GeneralParams (Basemodel): General collection parameters common to \
            multiple beamlines/experiments, such as exposure time, wavelength, ...
        metafile (Path | str): Path to _meta.h5 file.
        detector_name (str): Name of the detector in use for current experiment.
        tot_num_images (int, optional): Total number of frames in a collection.
        scan_axis (str, optional): Rotation scan axis. Must be passed for Tristan.
        axes_pos (list[GonioAxisPosition], optional): list of (axis_name, start, end) values for the \
            goniometer, passed from command line. Defaults to None.
        det_pos (list[DetAxisPosition], optional): List of (axis_name, start) values for the \
            detector, passed from command line. Defaults to None.
    """

    metafile: Path
    detector_name: DetectorName
    tot_num_images: Optional[int] = None
    scan_axis: Optional[str] = None
    axes_pos: Optional[list[GonioAxisPosition]] = None
    det_pos: Optional[list[DetAxisPosition]] = None

    @field_validator("metafile", mode="before")
    @classmethod
    def _parse_metafile(cls, metafile: str | Path):
        if isinstance(metafile, str):
            return Path(metafile)
        return metafile


def tristan_writer(
    master_file: Path,
    TR: CollectionParams,
    timestamps: tuple[str, str] = (None, None),
    notes: dict[str, Any] | None = None,
):
    """
    A function to call the nexus writer for Tristan 10M detector.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (CollectionParams): Parameters passed from the beamline.
        timestamps (tuple[str, str], optional): Collection start and end time. Defaults to (None, None).
        notes (dict[str, Any], optional): Dictionary of (key, value) pairs where key represents the \
            dataset name and value its data. Defaults to None.
    """
    source = Source("I19-2")

    # Define Tristan params
    tristan_params = TristanDetector("Tristan 10M", (3043, 4183))

    # Define Goniometer axes
    gonio_axes = I19_2Tristan.gonio
    # Define Detector
    det_axes = I19_2Tristan.det_axes

    # Update axes
    # Identify scan axis
    scan_axis = TR.scan_axis if TR.scan_axis else "phi"

    # Goniometer
    end_pos = None
    for gax in TR.axes_pos:
        idx = [n for n, ax in enumerate(gonio_axes) if ax.name == gax.id][0]
        gonio_axes[idx].start_pos = gax.start
        if gax.id == scan_axis and gax.start != gax.end:
            end_pos = gax.end

    # Detector
    for dax in TR.det_pos:
        idx = [n for n, ax in enumerate(det_axes) if ax.name == dax.id][0]
        det_axes[idx].start_pos = dax.start

    # Calculate scan range
    scan_idx = [n for n, ax in enumerate(gonio_axes) if ax.name == scan_axis][0]
    if not end_pos:
        end_pos = gonio_axes[scan_idx].end_pos
    OSC = {scan_axis: (gonio_axes[scan_idx].start_pos, end_pos)}

    # Define Detector
    detector = Detector(
        tristan_params,
        det_axes,
        TR.beam_center,
        TR.exposure_time,
        [I19_2Tristan.fast_axis, I19_2Tristan.slow_axis],
    )

    # Define Goniometer
    goniometer = Goniometer(gonio_axes, OSC)

    # Define beam and attenuator
    attenuator = Attenuator(TR.transmission)
    beam = Beam(TR.wavelength)

    collection_summary_log(
        logger,
        gonio_axes,
        detector,
        attenuator,
        beam,
        source,
        timestamps,
    )

    # Write
    try:
        EventFileWriter = EventNXmxFileWriter(
            master_file,
            goniometer,
            detector,
            source,
            beam,
            attenuator,
        )
        EventFileWriter.write(
            image_filename=TR.metafile.stem.replace("_meta", ""),
            start_time=timestamps[0],
        )
        if timestamps[1]:
            EventFileWriter.update_timestamps(timestamps[1], "end_time")
        if notes:
            # Write any additional info in /entry/notes
            EventFileWriter.add_NXnote(notes)
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        raise


def eiger_writer(
    master_file: Path,
    TR: CollectionParams,
    timestamps: tuple[str, str] = (None, None),
    use_meta: bool = False,
    n_frames: int | None = None,
    vds_offset: int = 0,
    notes: dict[str, Any] | None = None,
):
    """
    A function to call the NXmx nexus file writer for Eiger 2X 4M detector.
    If use_meta is set to False, then the parameter fields axes_pos and det_pos become required arguments.
    Otherwise, axes_pos and det_pos can be None but the code requires the information contained inside \
    the meta file be correct and readable.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (CollectionParams): Parameters passed from the beamline.
        timestamps (tuple[str, str], optional): Collection start and end time. Defaults to (None, None).
        use_meta (bool, optional): If True, metadata such as axes positions, wavelength etc. \
            will be updated using the meta.h5 file. Defaults to False.
        num_frames (int, optional): Number of images for the nexus file. Not necessary the same as the \
            tot_num_images from the CollectionParameters. If different, the VDS will only contain the \
            number of frames specified here. Defaults to None.
        vds_offset (int, optional): Start index for the vds writer. Defaults to 0.
        notes (dict[str, Any], optional): Dictionary of (key, value) pairs where key represents the \
            dataset name and value its data. Defaults to None.

    Raises:
        ValueError: If use_meta is set to False but axes_pos and det_pos haven't been passed.
        IOError: If the axes positions can't be read from the metafile (missing config or broken links).
    """
    if not use_meta:
        if TR.axes_pos is None or TR.det_pos is None:
            logger.error(
                """
                If not using the meta file, please pass the complete axis information for goniometer
                and/or detector.
                """
            )
            raise ValueError(
                "No meta file selected and missing at least one of axes_pos or det_pos from parameter model."
            )
        if n_frames is None and TR.tot_num_images is None:
            logger.error(
                """
                If not using the meta file, please make sure either the total number of images is passed \
                or the number of frames has been passed. These values could be the same for a standard \
                collection, or different if the vds needs to only point to part of the dataset.
                """
            )
            raise ValueError(
                "Neither total number of images nor number of frames have been passed to the model."
            )

    source = Source("I19-2")

    # Define Eiger 4M params
    eiger_params = EigerDetector(
        "Eiger 2X 4M",
        (2162, 2068),
        "CdTe",
        50649,
        -1,
    )

    # Read some parameters
    transmission = TR.transmission if TR.transmission else None
    wl = TR.wavelength
    beam_center = TR.beam_center

    # Define Goniometer axes
    gonio_axes = I19_2Eiger.gonio
    # Define Detector
    det_axes = I19_2Eiger.det_axes

    # Update axes
    if use_meta:
        logger.info("User requested to update metadata using meta file.")
        with h5py.File(TR.metafile, "r", libver="latest", swmr=True) as mh:
            meta = DectrisMetafile(mh)
            TR.tot_num_images = meta.get_full_number_of_images()
            logger.info(
                f"Total number of images for this collection found in meta file: {TR.tot_num_images}."
            )
            if not n_frames:
                n_frames = TR.tot_num_images
                logger.info(
                    "No specific numnber of frames requested, VDS will contain the full dataset."
                )
            vds_dtype = define_vds_data_type(meta)
            update_axes_from_meta(
                meta, gonio_axes, osc_axis=TR.scan_axis, use_config=True
            )
            update_axes_from_meta(meta, det_axes)
            # WARNING.det_z not in _dectris, but det_distance is. Getting that.

            logger.info(
                "Goniometer and detector axes positions have been updated with values from the meta file."
            )
            if TR.wavelength is None:
                logger.info(
                    "Wavelength hasn't been passed by user. Looking for it in the meta file."
                )
                wl = meta.get_wavelength()
            if TR.beam_center is None:
                logger.info(
                    "Beam center position has't been passed by user. Looking for it in the meta file."
                )
                beam_center = meta.get_beam_center()
    else:
        logger.info(
            "Not using meta file to update metadata, only the external links will be set up."
        )
        vds_dtype = np.uint32
        # Update axes
        # Goniometer
        for gax in TR.axes_pos:
            idx = [n for n, ax in enumerate(gonio_axes) if ax.name == gax.id][0]
            gonio_axes[idx].start_pos = gax.start
            if gax.inc != 0.0:
                gonio_axes[idx].increment = gax.inc

        # Detector
        for dax in TR.det_pos:
            idx = [n for n, ax in enumerate(det_axes) if ax.name == dax.id][0]
            det_axes[idx].start_pos = dax.start

        logger.info(
            "Goniometer and detector axes positions have been updated with values passed by the user."
        )

        if not n_frames:
            n_frames = TR.tot_num_images
        if not TR.tot_num_images:
            TR.tot_num_images = n_frames
            logger.warning(
                """
                As the total number of images was not set in the collection parameters, it has been set to \
                the requested number of frames.
                """
            )

    scan_axis = identify_osc_axis(gonio_axes)
    # Check that found scan_axis matches
    if scan_axis != TR.scan_axis:
        logger.warning(
            f"Scan axis {scan_axis} found different from requested one {TR.scan_axis}."
            f"Defaulting to {TR.scan_axis}. If wrong please check meta file."
        )
        scan_axis = TR.scan_axis
    scan_idx = [n for n, ax in enumerate(gonio_axes) if ax.name == scan_axis][0]
    gonio_axes[scan_idx].num_steps = n_frames
    OSC = calculate_scan_points(
        gonio_axes[scan_idx],
        rotation=True,
        tot_num_imgs=n_frames,
    )

    # Define beam and attenuator
    attenuator = Attenuator(transmission)
    beam = Beam(wl)

    # Define Detector
    detector = Detector(
        eiger_params,
        det_axes,
        beam_center,
        TR.exposure_time,
        [I19_2Eiger.fast_axis, I19_2Eiger.slow_axis],
    )

    # Define Goniometer
    goniometer = Goniometer(gonio_axes, OSC)

    collection_summary_log(
        logger,
        goniometer,
        detector,
        attenuator,
        beam,
        source,
        timestamps,
    )

    # Write
    try:
        image_filename = TR.metafile.as_posix().replace("_meta.h5", "")
        NXmx_writer = NXmxFileWriter(
            master_file,
            goniometer,
            detector,
            source,
            beam,
            attenuator,
            TR.tot_num_images,
        )
        NXmx_writer.write(image_filename=image_filename, start_time=timestamps[0])
        NXmx_writer.write_vds(
            vds_offset=vds_offset,
            vds_shape=(n_frames, *detector.detector_params.image_size),
            vds_dtype=vds_dtype,
        )
        if timestamps[1]:
            NXmx_writer.update_timestamps(timestamps[1], "end_time")
        if notes:
            NXmx_writer.add_NXnote(notes)
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        raise


def serial_nexus_writer(
    params: dict[str, Any],
    master_file: Path,
    timestamps: tuple[datetime, datetime] = (None, None),
    use_meta: bool = False,
    vds_offset: int = 0,
    n_frames: int | None = None,
    notes: dict[str, Any] | None = None,
):
    """Wrapper function to gather all parameters from the beamline and kick off the nexus writer for a \
    serial experiment on I19-2.

    Args:
        params (dict[str, Any]): Dictionary representation of CollectionParams.
        master_file (Path): Full path to the nexus file to be written.
        timestamps (tuple[str, str], optional): Start and end collection timestamps as datetime. \
            Defaults to (None, None).
        use_meta (bool, optional): Eiger option only, if True use metadata from meta.h5 file. Otherwise \
            all parameters will need to be passed manually. Defaults to False.
        vds_offset (int, optional): Start index for the vds writer. Defaults to 0.
        n_frames (int | None, optional): Number of images for the nexus file. Only needed if different \
            from the tot_num_images in the collection params. If passed, the VDS will only contain the \
            number of frames specified here. Defaults to None.
        notes (dict[str, Any] | None, optional): Any additional information to be written as NXnote, \
            passed as a dictionary of (key, value) pairs where key represents the dataset name and \
            value its data. Defaults to None.
    """
    collection_params = CollectionParams(**params)
    wdir = master_file.parent

    # Define a file handler
    logfile = wdir / "I19_2_nxs_writer.log"
    # Configure logging
    log.config(logfile.as_posix())

    logger.info("NeXus file writer for beamline I19-2 at DLS.")
    logger.info(
        f"Detector in use for this experiment: {collection_params.detector_name.value}."
    )
    logger.info(f"Current collection directory: {collection_params.metafile.parent}")

    # Get NeXus filename
    logger.info("NeXus file will be saved as %s" % master_file)

    # Get timestamps in the correct format if they aren't already
    start_time = timestamps[0].strftime("%Y-%m-%dT%H:%M:%S") if timestamps[0] else None
    stop_time = timestamps[1].strftime("%Y-%m-%dT%H:%M:%S") if timestamps[1] else None
    timestamps = (
        get_iso_timestamp(start_time),
        get_iso_timestamp(stop_time),
    )

    match collection_params.detector_name:
        case DetectorName.EIGER:
            eiger_writer(
                master_file,
                collection_params,
                timestamps,
                use_meta,
                n_frames,
                vds_offset,
                notes,
            )
        case DetectorName.TRISTAN:
            tristan_writer(master_file, collection_params, timestamps, notes)


def nexus_writer(
    params: dict[str, Any],
    master_file: Path,
    timestamps: tuple[datetime, datetime] = (None, None),
    use_meta: bool = False,
):
    """Wrapper function to gather all parameters from the beamline and kick off the nexus writer for a \
    standard experiment on I19-2.

    Args:
        params (dict[str, Any]): Dictionary representation of CollectionParams.
        master_file (Path): Full path to the nexus file to be written.
        timestamps (tuple[str, str], optional): Start and end collection timestamps as datetime. \
            Defaults to (None, None).
        use_meta (bool, optional): Eiger option only, if True use metadata from meta.h5 file. Otherwise \
            all parameters will need to be passed manually. Defaults to False.
    """
    collection_params = CollectionParams(**params)
    wdir = master_file.parent

    # Define a file handler
    logfile = wdir / "I19_2_nxs_writer.log"
    # Configure logging
    log.config(logfile.as_posix())

    logger.info("NeXus file writer for beamline I19-2 at DLS.")
    logger.info(
        f"Detector in use for this experiment: {collection_params.detector_name}."
    )
    logger.info(f"Current collection directory: {collection_params.metafile.parent}")

    # Add some information to logger
    logger.info("Creating a NeXus file for %s ..." % collection_params.metafile.name)
    logger.info("NeXus file will be saved as %s" % master_file)

    # Get timestamps in the correct format if they aren't already
    start_time = timestamps[0].strftime("%Y-%m-%dT%H:%M:%S") if timestamps[0] else None
    stop_time = timestamps[1].strftime("%Y-%m-%dT%H:%M:%S") if timestamps[1] else None
    timestamps = (
        get_iso_timestamp(start_time),
        get_iso_timestamp(stop_time),
    )

    if collection_params.detector_name is DetectorName.TRISTAN:
        if not collection_params.axes_pos or not collection_params.det_pos:
            logger.error("Please pass the axes positions for a Tristan collection.")
            raise ValueError(
                "Missing goniometer and/or detector axes information for tristan collection"
            )
        if collection_params.scan_axis is None:
            logger.warning(
                "No scan axis has been specified. Phi will be set as default."
            )
            collection_params.scan_axis = "phi"

    if not use_meta:
        if (
            not collection_params.tot_num_images
            and collection_params.detector_name is DetectorName.EIGER
        ):
            raise ValueError(
                """
                Missing input parameter n_imgs. \n
                For an Eiger collection, if meta file is to be ignored, the number of images to
                be collected has to be passed to the writer.
                """
            )
        if collection_params.beam_center == (0, 0):
            logger.warning(
                """
                Beam centre was not passed to the writer.
                As it won't be updated from the meta file, it will be set to (0, 0).
                """
            )

    match collection_params.detector_name:
        case DetectorName.EIGER:
            eiger_writer(
                master_file,
                collection_params,
                timestamps,
                use_meta,
            )
        case DetectorName.TRISTAN:
            tristan_writer(
                master_file,
                collection_params,
                timestamps,
            )
