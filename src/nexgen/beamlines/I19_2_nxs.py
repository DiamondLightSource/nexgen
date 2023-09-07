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
from ..utils import get_iso_timestamp, get_nexus_filename
from .beamline_utils import collection_summary_log


class ExperimentTypeError(Exception):
    pass


# Define a logger object
logger = logging.getLogger("nexgen.I19-2_NeXus")

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
    TR: namedtuple,
    timestamps: Tuple[str, str] = (None, None),
    axes_pos: List[namedtuple] = None,
    det_pos: List[namedtuple] = None,
):
    """
    A function to call the nexus writer for Tristan 10M detector.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (namedtuple): Parameters passed from the beamline.
        timestamps (Tuple[str, str], optional): Collection start and end time. Defaults to (None, None).
        axes_pos (List[namedtuple], optional): List of (axis_name, start, end) values for the goniometer, passed from command line. Defaults to None.
        det_pos (List[namedtuple], optional): List of (axis_name, start) values for the detector, passed from command line. Defaults to None.
    """
    source = Source("I19-2")
    from .beamline_utils import I19_2Tristan as axes_params

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
        EventFileWriter.write()
        EventFileWriter.update_timestamps(timestamps)
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        raise


def eiger_writer(
    master_file: Path,
    TR: namedtuple,
    timestamps: Tuple[str, str] = (None, None),
):
    """
    A function to call the NXmx nexus file writer for Eiger 2X 4M detector.
    It requires the informatin contained inside the meta file to work correctly.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (namedtuple): Parameters passed from the beamline.
        timestamps (Tuple[str, str], optional): Collection start and end time. Defaults to (None, None).

    Raises:
        IOError: If the axes positions can't be read from the metafile (missing config or broken links).
    """
    source = Source("I19-2")
    from .beamline_utils import I19_2Eiger as axes_params

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
    with h5py.File(TR.meta_file, "r", libver="latest", swmr=True) as mh:
        meta = DectrisMetafile(mh)
        n_frames = meta.get_number_of_images()
        logger.info(f"Number of images found in meta file: {n_frames}.")
        vds_dtype = define_vds_data_type(meta)
        update_axes_from_meta(meta, gonio_axes)
        update_axes_from_meta(meta, det_axes)
        # WARNING.det_z not in _dectris, but det_distance is. Getting that.

        logger.info(
            "Goniometer and detector axes positions have been updated with values from the meta file."
        )
        if TR.wavelength is None:
            logger.info(
                "Wavelength has't been passed by user. Looking for it in the meta file."
            )
            wl = meta.get_wavelength()
        if TR.beam_center is None:
            logger.info(
                "Beam center position has't been passed by user. Looking for it in the meta file."
            )
            beam_center = meta.get_beam_center()

    scan_axis = identify_osc_axis(gonio_axes)
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
        NXmx_writer.update_timestamps((None, timestamps[1]))
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
        scan_axis (str, optional): Name of the oscillation axis. Defaults to phi.
        start_time (datetime, optional): Experiment start time. Defaults to None.
        stop_time (datetime, optional): Experiment end time. Defaults to None.

    Keyword Args:
        exposure_time (float): Exposure time, in s.
        transmission (float): Attenuator transmission, in %.
        wavelength (float): Wavelength of incident beam, in A.
        beam_center (List[float, float]): Beam center position, in pixels.
        gonio_pos (List[namedtuple(str, float, float)]): Name, start and end positions \
            of the goniometer axes.
        det_pos (List[namedtuple(str, float, float)]): Name, start and end positions \
            of detector axes.
        outdir (str): Directory where to save the file. Only specify if different \
            from meta_file directory.
        serial (bool): Specify whether it's a serial crystallography dataset.
        det_dist (float): Distance between sample and detector, in mm.
    """
    if "serial" in list(params.keys()) and params["serial"] is True:
        raise ExperimentTypeError(
            "This is writer is not enabled for ssx collections."
            "Pleas look into SSX_Eiger or SSX_Tristan for this functionality."
        )

    TR = tr_collect(
        meta_file=Path(meta_file).expanduser().resolve(),
        detector_name=detector_name,
        exposure_time=params["exposure_time"],
        transmission=params["transmission"],
        wavelength=params["wavelength"],
        beam_center=params["beam_center"],
        start_time=start_time.strftime("%Y-%m-%dT%H:%M:%S") if start_time else None,
        stop_time=stop_time.strftime("%Y-%m-%dT%H:%M:%S") if stop_time else None,
        scan_axis=scan_axis,
    )

    # Check that the new NeXus file is to be written in the same directory
    if "outdir" in list(params.keys()) and params["outdir"]:
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

    if "tristan" in TR.detector_name.lower():
        if params["gonio_pos"] is None or params["det_pos"] is None:
            logger.error("Please pass the axes positions for a Tristan collection.")
        if TR.scan_axis is None:
            logger.warning(
                "No scan axis has been specified. Phi will be set as default."
            )

    if "eiger" in TR.detector_name.lower():
        eiger_writer(master_file, TR, timestamps)
    elif "tristan" in TR.detector_name.lower():
        tristan_writer(
            master_file, TR, timestamps, params["gonio_pos"], params["det_pos"]
        )
