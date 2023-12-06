"""
Create a NeXus file for time-resolved collections on I19-2.
"""
from __future__ import annotations

import logging
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import h5py
import numpy as np

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
from ..nxs_utils.ScanUtils import calculate_scan_points, identify_osc_axis
from ..nxs_write.NXmxWriter import EventNXmxFileWriter, NXmxFileWriter
from ..tools.Metafile import DectrisMetafile
from ..tools.MetaReader import define_vds_data_type, update_axes_from_meta
from ..utils import find_in_dict, get_iso_timestamp, get_nexus_filename
from .beamline_utils import collection_summary_log


class ExperimentTypeError(Exception):
    pass


# Define a logger object
logger = logging.getLogger("nexgen.I19-2_NeXus")


# Useful axis definitions
axes = namedtuple("axes", ("id", "start", "inc", "end"), defaults=(None, 0.0, 0.0, 0.0))
axes.__doc__ = """Goniometer axis name, start and end position, increment."""
det_axes = namedtuple("det_axes", ("id", "start"), defaults=(None, 0.0))
det_axes.__doc__ = """Detector axis name and position."""


# Define experiment metadata
tr_collect = namedtuple(
    "tr_collect",
    [
        "meta_file",
        "detector_name",
        "exposure_time",
        "transmission",
        "wavelength",
        "beam_center",
        "start_time",
        "stop_time",
        "scan_axis",
    ],
)

tr_collect.__doc__ = """Parameters passed as input from the beamline."""
tr_collect.meta_file.__doc__ = "Path to _meta.h5 file."
tr_collect.detector_name.__doc__ = "Name of the detector in use for current experiment."
tr_collect.exposure_time.__doc__ = "Exposure time, in s."
tr_collect.transmission.__doc__ = "Attenuator transmission, in %."
tr_collect.wavelength.__doc__ = "Incident beam wavelength, in A."
tr_collect.beam_center.__doc__ = "Beam center (x,y) position, in pixels."
tr_collect.start_time.__doc__ = "Collection start time."
tr_collect.stop_time.__doc__ = "Collection end time."
tr_collect.scan_axis.__doc__ = "Rotation scan axis. Must be passed for Tristan."


def tristan_writer(
    master_file: Path,
    TR: tr_collect,
    timestamps: Tuple[str, str] = (None, None),
    axes_pos: List[axes] = None,
    det_pos: List[det_axes] = None,
):
    """
    A function to call the nexus writer for Tristan 10M detector.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (tr_collect): Parameters passed from the beamline.
        timestamps (Tuple[str, str], optional): Collection start and end time. Defaults to (None, None).
        axes_pos (List[axes], optional): List of (axis_name, start, end) values for the \
            goniometer, passed from command line. Defaults to None.
        det_pos (List[det_axes], optional): List of (axis_name, start) values for the \
            detector, passed from command line. Defaults to None.
    """
    source = Source("I19-2")
    from .I19_2_params import I19_2Tristan as axes_params

    # Define Tristan params
    tristan_params = TristanDetector("Tristan 10M", (3043, 4183))

    # Define Goniometer axes
    gonio_axes = axes_params.gonio
    # Define Detector
    det_axes = axes_params.det_axes

    # Update axes
    # Goniometer
    end_pos = None
    for gax in axes_pos:
        idx = [n for n, ax in enumerate(gonio_axes) if ax.name == gax.id][0]
        gonio_axes[idx].start_pos = gax.start
        if gax.start != gax.end:
            end_pos = gax.end

    # Detector
    for dax in det_pos:
        idx = [n for n, ax in enumerate(det_axes) if ax.name == dax.id][0]
        det_axes[idx].start_pos = dax.start

    # Identify scan axis and calculate scan range
    scan_axis = TR.scan_axis if TR.scan_axis else "phi"
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
        [axes_params.fast_axis, axes_params.slow_axis],
    )

    # Define Goniometer
    goniometer = Goniometer(gonio_axes, OSC)

    # Define beam and attenuator
    attenuator = Attenuator(TR.transmission)
    beam = Beam(TR.wavelength)

    collection_summary_log(
        logger,
        gonio_axes,
        [scan_axis],
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
        EventFileWriter.write(start_time=timestamps[0])
        if timestamps[1]:
            EventFileWriter.update_timestamps(timestamps[1], "end_time")
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        raise


def eiger_writer(
    master_file: Path,
    TR: tr_collect,
    timestamps: Tuple[str, str] = (None, None),
    use_meta: bool = False,
    n_frames: int | None = None,
    axes_pos: List[axes] = None,
    det_pos: List[det_axes] = None,
):
    """
    A function to call the NXmx nexus file writer for Eiger 2X 4M detector.
    If use_meta is set to False, axes_pos and det_pos become required arguments. Otherwise, \
    axes_pos and det_pos can be None but the code requires the information contained inside \
    the meta file to work correctly.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (tr_collect): Parameters passed from the beamline.
        timestamps (Tuple[str, str], optional): Collection start and end time. Defaults to (None, None).
        use_meta (bool, optional): If True, metadata such as axes positions, wavelength etc. \
            will be updated using the meta.h5 file. Defaults to False.
        num_frames (int, optional): Total number of images to be collected. Defaults to None.
        axes_pos (List[axes], optional): List of (axis_name, start, inc) values for the \
            goniometer, passed from command line. Defaults to None.
        det_pos (List[det_axes], optional): List of (axis_name, start) values for the \
            detector, passed from command line. Defaults to None.

    Raises:
        ValueError: If use_meta is set to False but axes_pos and det_pos haven't been passed.
        IOError: If the axes positions can't be read from the metafile (missing config or broken links).
    """
    if not use_meta:
        if axes_pos is None or det_pos is None or n_frames is None:
            logger.error(
                """
                If not using the meta file, please pass the complete axis information for goniometer
                and/or detector. Also make sure that the number of frames was passed.
                """
            )
            raise ValueError("Missing at least one of axes_pos, det_pos, n_frames.")

    source = Source("I19-2")
    from .I19_2_params import I19_2Eiger as axes_params

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
    gonio_axes = axes_params.gonio
    # Define Detector
    det_axes = axes_params.det_axes

    # Update axes
    if use_meta:
        logger.info("User requested to update metadata using meta file.")
        with h5py.File(TR.meta_file, "r", libver="latest", swmr=True) as mh:
            meta = DectrisMetafile(mh)
            n_frames = meta.get_number_of_images()
            logger.info(f"Number of images found in meta file: {n_frames}.")
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
        for gax in axes_pos:
            idx = [n for n, ax in enumerate(gonio_axes) if ax.name == gax.id][0]
            gonio_axes[idx].start_pos = gax.start
            if gax.inc != 0.0:
                gonio_axes[idx].increment = gax.inc

        # Detector
        for dax in det_pos:
            idx = [n for n, ax in enumerate(det_axes) if ax.name == dax.id][0]
            det_axes[idx].start_pos = dax.start
            logger.info(
                "Goniometer and detector axes positions have been updated with values passed by the user."
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
        [axes_params.fast_axis, axes_params.slow_axis],
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
        NXmx_writer = NXmxFileWriter(
            master_file,
            goniometer,
            detector,
            source,
            beam,
            attenuator,
            n_frames,
        )
        NXmx_writer.write(start_time=timestamps[0])
        NXmx_writer.write_vds(
            vds_shape=(n_frames, *detector.detector_params.image_size),
            vds_dtype=vds_dtype,
        )
        if timestamps[1]:
            NXmx_writer.update_timestamps(timestamps[1], "end_time")
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        raise


def nexus_writer(
    meta_file: Path | str,
    detector_name: str,
    exposure_time: float,
    scan_axis: str = "phi",
    start_time: datetime | None = None,
    stop_time: datetime | None = None,
    **params,
):
    """
    Gather all parameters from the beamline and call the NeXus writers.

    Args:
        meta_file (Path | str): Path to _meta.h5 file.
        detector_name (str): Detector in use.
        exposure_time (float): Exposure time, in s.
        scan_axis (str, optional): Name of the oscillation axis. Defaults to phi.
        start_time (datetime, optional): Experiment start time. Defaults to None.
        stop_time (datetime, optional): Experiment end time. Defaults to None.

    Keyword Args:
        n_imgs (int): Total number of images to be collected.
        transmission (float): Attenuator transmission, in %.
        wavelength (float): Wavelength of incident beam, in A.
        beam_center (List[float, float]): Beam center position, in pixels.
        gonio_pos (List[axes]): Name, start and end positions \
            of the goniometer axes.
        det_pos (List[det_axes]): Name, start and end positions \
            of detector axes.
        outdir (str): Directory where to save the file. Only specify if different \
            from meta_file directory.
        serial (bool): Specify whether it's a serial crystallography dataset.
        det_dist (float): Distance between sample and detector, in mm.
        use_meta (bool): For Eiger, if True use metadata from meta.h5 file. Otherwise \
            will require all other information to be passed manually.
    """
    if find_in_dict("serial", params) and params["serial"] is True:
        raise ExperimentTypeError(
            "This is writer is not enabled for ssx collections."
            "Pleas look into SSX_Eiger or SSX_Tristan for this functionality."
        )

    TR = tr_collect(
        meta_file=Path(meta_file).expanduser().resolve(),
        detector_name=detector_name.lower(),
        exposure_time=exposure_time,
        transmission=params["transmission"]
        if find_in_dict("transmission", params)
        else None,
        wavelength=params["wavelength"] if find_in_dict("wavelength", params) else None,
        beam_center=params["beam_center"]
        if find_in_dict("beam_center", params)
        else (0, 0),
        start_time=start_time.strftime("%Y-%m-%dT%H:%M:%S") if start_time else None,
        stop_time=stop_time.strftime("%Y-%m-%dT%H:%M:%S") if stop_time else None,
        scan_axis=scan_axis,
    )

    # Check that the new NeXus file is to be written in the same directory
    if find_in_dict("outdir", params) and params["outdir"]:
        wdir = Path(params["outdir"]).expanduser().resolve()
    else:
        wdir = TR.meta_file.parent

    # Define a file handler
    logfile = wdir / "I19_2_nxs_writer.log"
    # Configure logging
    log.config(logfile.as_posix())

    logger.info("NeXus file writer for beamline I19-2 at DLS.")
    logger.info(f"Detector in use for this experiment: {TR.detector_name}.")
    logger.info(f"Current collection directory: {TR.meta_file.parent}")

    # Add some information to logger
    logger.info("Creating a NeXus file for %s ..." % TR.meta_file.name)
    # Get NeXus filename
    master_file = get_nexus_filename(TR.meta_file)
    master_file = wdir / master_file.name
    logger.info("NeXus file will be saved as %s" % master_file)

    # Get timestamps in the correct format if they aren't already
    timestamps = (
        get_iso_timestamp(TR.start_time),
        get_iso_timestamp(TR.stop_time),
    )

    if not find_in_dict("gonio_pos", params):
        params["gonio_pos"] = None
    if not find_in_dict("det_pos", params):
        params["det_pos"] = None

    if "tristan" in TR.detector_name.lower():
        if params["gonio_pos"] is None or params["det_pos"] is None:
            logger.error("Please pass the axes positions for a Tristan collection.")
            raise ValueError(
                "Missing goniometer and/or detector axes information for tristan collection"
            )
        if TR.scan_axis is None:
            logger.warning(
                "No scan axis has been specified. Phi will be set as default."
            )

    if not find_in_dict("use_meta", params):
        # If by any chance not passed, assume False
        params["use_meta"] = False

    if params["use_meta"] is True:
        params["gonio_pos"] = None
        params["det_pos"] = None
    else:
        if not find_in_dict("n_imgs", params) and "eiger" in TR.detector_name:
            raise ValueError(
                """
                Missing input parameter n_imgs. \n
                For an Eiger collection, if meta file is to be ignored, the number of images to
                be collected has to be passed to the writer.
                """
            )
        if TR.beam_center == (0, 0):
            logger.warning(
                """
                Beam centre was not passed to the writer.
                As it won't be updated from the meta file, it will be set to (0, 0).
                """
            )

    if "eiger" in TR.detector_name:
        if not find_in_dict("n_imgs", params):
            params["n_imgs"] = None
        eiger_writer(
            master_file,
            TR,
            timestamps,
            params["use_meta"],
            params["n_imgs"],
            params["gonio_pos"],
            params["det_pos"],
        )
    elif "tristan" in TR.detector_name:
        tristan_writer(
            master_file, TR, timestamps, params["gonio_pos"], params["det_pos"]
        )
