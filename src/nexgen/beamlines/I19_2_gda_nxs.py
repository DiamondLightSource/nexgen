"""
Create a NeXus file for time-resolved collections on I19-2 using parameters passed from GDA.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from numpy.typing import DTypeLike

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
from ..nxs_utils.detector import DetectorType, UnknownDetectorTypeError
from ..nxs_utils.scan_utils import calculate_scan_points
from ..nxs_write.nxmx_writer import EventNXmxFileWriter, NXmxFileWriter
from ..utils import find_in_dict, get_iso_timestamp, get_nexus_filename
from .beamline_utils import BeamlineAxes, GeneralParams, collection_summary_log
from .GDAtools.ExtendedRequest import (
    ExtendedRequestIO,
    read_det_position_from_xml,
    read_scan_from_xml,
)
from .GDAtools.GDAjson2params import JSONParamsIO

# Define a logger object and a formatter
logger = logging.getLogger("nexgen.I19-2_NeXus_gda")


class GDACollectionParams(GeneralParams):
    """Collection parameters for I19-2 with information extracted from GDA.

    Args:
        GeneralParams (Basemodel): General collection parameters common to \
            multiple beamlines/experiments, such as exposure time, wavelength, ...
        meta_file (Path | str): Path to _meta.h5 file.
        xml_file (Path | str):
        detector_name (str): Name of the detector in use for current experiment.
        geometry_json (Path | str, optional): Path to GDA config JSON file \
            describing the beamline geometry.
        detector_json (Path | str, optional): Path to GDA config JSON file \
            describing the detector.
    """

    meta_file: Path | str
    xml_file: Path | str
    detector_name: str
    geometry_json: Optional[Path | str]
    detector_json: Optional[Path | str]


def tristan_writer(
    master_file: Path,
    TR: GDACollectionParams,
    axes_params: BeamlineAxes,
    det_params: DetectorType,
    timestamps: tuple[str, str] = (None, None),
):
    """
    A function to call the nexus writer for Tristan 10M detector.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (namedtuple): Parameters passed from the beamline.
        axes_params (BeamlineAxes): Axes for goniometer, detector and detector module.
        det_params (DetectorType): Detector definition for Tristan.
        timestamps (tuple[str, str], optional): Collection start and end time. Defaults to None.
    """
    ecr = ExtendedRequestIO(TR.xml_file)
    # Read information from xml file
    logger.info("Read xml file.")
    scan_axis, pos, _ = read_scan_from_xml(ecr)
    # n_Frames is only useful for eiger
    # pos[scan_axis][::-1] is scan range
    scan_range = pos[scan_axis][:-1]
    # Define OSC scans dictionary
    OSC = {scan_axis: scan_range}

    det_positions = read_det_position_from_xml(ecr, det_params.description)

    # Attenuator
    attenuator = Attenuator(ecr.getTransmission())

    # Beam
    beam = Beam(TR.wavelength)

    # Source
    source = Source("I19-2")

    # Detector
    det_axes = axes_params.det_axes
    det_axes[0].start_pos = det_positions[0]  # two_theta
    det_axes[1].start_pos = det_positions[1]  # det_z
    detector = Detector(
        det_params,
        det_axes,
        TR.beam_center,
        TR.exposure_time,
        [axes_params.fast_axis, axes_params.slow_axis],
    )

    # Goniometer
    gonio_axes = axes_params.gonio
    for k, v in pos.items():
        # Get correct start positions
        idx = [n for n, ax in enumerate(gonio_axes) if ax.name == k][0]
        gonio_axes[idx].start_pos = v[0]
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

    # Get on with the writing now...
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


def eiger_writer(
    master_file: Path,
    TR: GDACollectionParams,
    axes_params: BeamlineAxes,
    det_params: DetectorType,
    timestamps: tuple[str, str] = (None, None),
    vds_dtype: DTypeLike = np.uint16,
):
    """
    A function to call the nexus writer for Eiger 2X 4M detector.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (namedtuple): Parameters passed from the beamline.
        axes_params (BeamlineAxes): Axes for goniometer, detector and detector module.
        det_params (DetectorType): Detector definition for Eiger.
        timestamps (tuple[str, str], optional): Collection start and end time. Defaults to (None, None).
        vds_dtype (DtypeLike): Data type for vds as np.uint##.
    """
    ecr = ExtendedRequestIO(TR.xml_file)
    # Read information from xml file
    logger.info("Read xml file.")
    scan_axis, pos, n_frames = read_scan_from_xml(ecr)

    det_positions = read_det_position_from_xml(ecr, det_params.description)

    # Attenuator
    attenuator = Attenuator(ecr.getTransmission())

    # Beam
    beam = Beam(TR.wavelength)

    # Source
    source = Source("I19-2")

    # Detector
    det_axes = axes_params.det_axes
    det_axes[0].start_pos = det_positions[0]  # two_theta
    det_axes[1].start_pos = det_positions[1]  # det_z
    detector = Detector(
        det_params,
        det_axes,
        TR.beam_center,
        TR.exposure_time,
        [axes_params.fast_axis, axes_params.slow_axis],
    )

    # Goniometer
    gonio_axes = axes_params.gonio
    for k, v in pos.items():
        # Get correct start positions
        idx = [n for n, ax in enumerate(gonio_axes) if ax.name == k][0]
        gonio_axes[idx].start_pos = v[0]

    # Get scan range array
    logger.info("Calculating scan range...")
    scan_idx = [n for n, ax in enumerate(gonio_axes) if ax.name == scan_axis][0]

    # Define OSC scans dictionary
    OSC = calculate_scan_points(
        gonio_axes[scan_idx], rotation=True, tot_num_imgs=n_frames
    )

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

    # Get on with the writing now...
    try:
        NXmx_Writer = NXmxFileWriter(
            master_file,
            goniometer,
            detector,
            source,
            beam,
            attenuator,
            n_frames,
        )
        NXmx_Writer.write(start_time=timestamps[0])
        if timestamps[1]:
            NXmx_Writer.update_timestamps(timestamps[1], "end_time")
        NXmx_Writer.write_vds(
            vds_shape=(n_frames, *detector.detector_params.image_size),
            vds_dtype=vds_dtype,
        )
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )


def write_nxs(
    meta_file: Path | str,
    xml_file: Path | str,
    detector_name: str,
    exposure_time: float,
    wavelength: float,
    beam_center: list[float, float],
    start_time: datetime | None = None,
    stop_time: datetime | None = None,
    **tr_params,
):
    """
    Gather all parameters from the beamline and call the NeXus writers.

    Args:
        meta_file (Path | str): Path to _meta.h5 file.
        xml_file (Path | str): Path to gda-generated xml file.
        detector_name (str): Detector in use.
        exposure_time (float): Exposure time, in s.
        wavelength (float): Wavelength of incident beam, in A.
        beam_center (list[float, float]): Beam center position, in pixels.
        start_time (datetime, optional): Experiment start time. Defaults to None.
        stop_time (datetime, optional): Experiment end time. Defaults to None.

    Keyword Args:
        geometry_json (Path | str): Path to GDA generated geometry json file.
        detector_json (Path | str): Path to GDA generated detector json file.
        vds_dtype (DtypeLike): Data type for vds as np.uint##.
    """
    # Get info from the beamline
    TR = GDACollectionParams(
        meta_file=Path(meta_file).expanduser().resolve(),
        xml_file=Path(xml_file).expanduser().resolve(),
        detector_name=detector_name,
        exposure_time=exposure_time,
        wavelength=wavelength,
        beam_center=beam_center,
        geometry_json=(
            tr_params["geometry_json"]
            if find_in_dict("geometry_json", tr_params)
            else None
        ),
        detector_json=(
            tr_params["detector_json"]
            if find_in_dict("detector_json", tr_params)
            else None
        ),
    )

    # Define a file handler
    logfile = TR.meta_file.parent / "nexus_writer.log"
    # Configure logging
    log.config(logfile.as_posix())

    logger.info("NeXus file writer for beamline I19-2 at DLS.")
    logger.info(f"Detector in use for this experiment: {TR.detector_name}.")
    logger.info(f"Current collection directory: {TR.meta_file.parent}")
    # Add some information to logger
    logger.info("Creating a NeXus file for %s ..." % TR.meta_file.name)
    # Get NeXus filename
    master_file = get_nexus_filename(TR.meta_file)
    logger.info("NeXus file will be saved as %s" % master_file)

    # Get some parameters in here
    if "eiger" in TR.detector_name.lower():
        from .I19_2_params import I19_2Eiger as axes_params

        det_params = EigerDetector(
            "Eiger 2X 4M",
            (2162, 2068),
            "CdTe",
            50649,
            -1,
        )
    elif "tristan" in TR.detector_name.lower():
        from .I19_2_params import I19_2Tristan as axes_params

        det_params = TristanDetector("Tristan 10M", (3043, 4183))
        # Temporary worksround, flatfield from gda has different file name
        det_params.constants["flatfield"] = (
            "Tristan10M_flat_field_coeff_with_Mo_17.479keV.h5"
        )
    else:
        raise UnknownDetectorTypeError("Unknown detector name passed.")

    # Get goniometer and detector parameters
    if TR.geometry_json:
        logger.info("Reading geometry from json file.")
        gonio_axes = JSONParamsIO(TR.geometry_json).get_goniometer_axes_from_file()
        det_axes = JSONParamsIO(TR.geometry_json).get_detector_axes_from_file()
        # Overwrite
        axes_params.gonio = gonio_axes
        axes_params.det_axes = det_axes

    if TR.detector_json:
        logger.info("Reading detector parameters from json file.")
        det_params = JSONParamsIO(TR.detector_json).get_detector_params_from_file()
        fast_axis, slow_axis = JSONParamsIO(
            TR.detector_json
        ).get_fast_and_slow_direction_vectors_from_file(det_params.description)
        # Overwrite
        axes_params.fast_axis = fast_axis
        axes_params.slow_axis = slow_axis

    # Get timestamps in the correct format if they aren't already
    _start_time = (
        start_time.strftime("%Y-%m-%dT%H:%M:%S") if start_time else None
    )  # This should be datetiem type
    _stop_time = stop_time.strftime("%Y-%m-%dT%H:%M:%S") if stop_time else None  # idem.
    timestamps = (
        get_iso_timestamp(_start_time),
        get_iso_timestamp(_stop_time),
    )

    if "tristan" in TR.detector_name:
        tristan_writer(master_file, TR, axes_params, det_params, timestamps)
    else:
        vds_dtype = (
            np.uint16
            if not find_in_dict("vds_dtype", tr_params)
            else tr_params["vds_dtype"]
        )
        eiger_writer(master_file, TR, axes_params, det_params, timestamps, vds_dtype)
