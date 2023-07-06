"""
Create a NeXus file for time-resolved collections on I19-2 using parameters passed from GDA.
"""
from __future__ import annotations

import logging
from collections import namedtuple
from pathlib import Path
from typing import List, Tuple

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
from ..nxs_utils.Detector import DetectorType, UnknownDetectorTypeError
from ..nxs_utils.ScanUtils import calculate_scan_points
from ..nxs_write.NXmxWriter import EventNXmxFileWriter, NXmxFileWriter
from ..utils import get_iso_timestamp, get_nexus_filename
from .beamline_parameters import BeamlineAxes
from .GDAtools.ExtendedRequest import ExtendedRequestIO
from .GDAtools.GDAjson2params import JSONParamsIO

# Define a logger object and a formatter
logger = logging.getLogger("nexgen.I19-2_NeXus_gda")

tr_collect = namedtuple(
    "tr_collect",
    [
        "meta_file",
        "xml_file",
        "detector_name",
        "exposure_time",
        "wavelength",
        "beam_center",
        "start_time",
        "stop_time",
        "geometry_json",  # Define these 2 as None
        "detector_json",
    ],
)

tr_collect.__doc__ = (
    """Information extracted from GDA containing collection parameters."""
)
tr_collect.meta_file.__doc__ = "Path to _meta.h5 file."
tr_collect.xml_file.__doc__ = "Path to GDA-generated xml file."
tr_collect.detector_name.__doc__ = "Name of the detector in use for current experiment."
tr_collect.exposure_time.__doc__ = "Exposure time, in s."
tr_collect.wavelength.__doc__ = "Incident beam wavelength, in A."
tr_collect.beam_center.__doc__ = "Beam center (x,y) position, in pixels."
tr_collect.start_time.__doc__ = "Collection start time."
tr_collect.stop_time.__doc__ = "Collection end time."
tr_collect.geometry_json.__doc__ = (
    "Path to GDA-generated JSON file describing the beamline geometry."
)
tr_collect.detector_json.__doc__ = (
    "Path to GDA-generated JSON file describing the detector."
)


def log_collection_summary(
    gonio_axes, osc_axis, detector, attenuator, beam, source, timestamps
):
    # TODO improve logging
    logger.info("--- COLLECTION SUMMARY ---")
    logger.info("Source information")
    logger.info(f"Facility: {source.name} - {source.facility_type}.")
    logger.info(f"Beamline: {source.beamline}")

    logger.info(f"Incident beam wavelength: {beam.wavelength}")
    logger.info(f"Attenuation: {attenuator.transmission}")

    logger.info("Goniometer information")
    logger.info(f"Scan axis is: {osc_axis}")
    for ax in gonio_axes:
        logger.info(
            f"Goniometer axis: {ax.name} => {ax.start_pos}, {ax.transformation_type} on {ax.depends}"
        )
    logger.info("Detector information")
    logger.info(f"{detector.detector_params.description}")
    logger.info(
        f"Sensor made of {detector.detector_params.sensor_material} x {detector.detector_params.sensor_thickness}"
    )
    logger.info(
        f"Detector is a {detector.detector_params.image_size[::-1]} array of {detector.detector_params.pixel_size} pixels"
    )
    for ax in detector.det_axes:
        logger.info(
            f"Detector axis: {ax.name} => {ax.start_pos}, {ax.transformation_type} on {ax.depends}"
        )

    logger.info(f"Recorded beam center is: {detector.beam_center}.")
    logger.info(f"Timestamps recorded: {timestamps}")


def read_scan_from_xml(ecr: ExtendedRequestIO):
    """
    Extract information about the scan contained in the xml file.

    Args:
        ecr (ExtendedRequestIO): XML tree parser.
        xmlfile (Path | str): Path to xml file.

    Returns:
        scan_axis (str): Name of the rotation scan axis
        pos (Dict): Dictionary containing the (start,end,increment) values for each goniometer axis.
        num (int): Number of images written.
    """
    # Goniometer
    osc_seq = ecr.getOscillationSequence()
    # Find scan range
    if osc_seq["range"] == 0.0:
        scan_range = (osc_seq["start"], osc_seq["start"])
        num = osc_seq["number_of_images"]
    else:
        start = osc_seq["start"]
        num = osc_seq["number_of_images"]
        stop = start + num * osc_seq["range"]
        scan_range = (start, stop)
    # Determine scan axis
    if ecr.getAxisChoice() == "omega":
        scan_axis = "omega"
        omega_pos = (*scan_range, osc_seq["range"])  # 0.0)
        phi_pos = (*2 * (ecr.getOtherAxis(),), 0.0)
    else:
        scan_axis = "phi"
        phi_pos = (*scan_range, osc_seq["range"])  # 0.0)
        omega_pos = (*2 * (ecr.getOtherAxis(),), 0.0)
    kappa_pos = (*2 * (ecr.getKappa(),), 0.0)

    pos = {
        "omega": omega_pos,
        "phi": phi_pos,
        "kappa": kappa_pos,
        "sam_x": (0.0, 0.0, 0.0),
        "sam_y": (0.0, 0.0, 0.0),
        "sam_z": (0.0, 0.0, 0.0),
    }

    return scan_axis, pos, int(num)


def read_det_position_from_xml(
    ecr: ExtendedRequestIO,
    det_description: str,
) -> List[float]:
    """Extract the detector position contained in the xml file.

    Args:
        ecr (ExtendedRequestIO): XML tree parser.
        det_description (str): Detector description

    Returns:
        List[float]: Detector axes positions in the order [2theta, det_z]
    """
    if "tristan" in det_description.lower():
        return [0.0, ecr.getSampleDetectorDistance()]
    elif "eiger" in det_description.lower():
        return [ecr.getTwoTheta(), ecr.getSampleDetectorDistance()]
    logger.warning(
        "Unrecognized detector description. Setting two_theta to 0.0 to be safe."
    )
    return [0.0, ecr.getSampleDetectorDistance()]


def tristan_writer(
    master_file: Path,
    TR: namedtuple,
    axes_params: BeamlineAxes,
    det_params: DetectorType,
    timestamps: Tuple[str, str] = (None, None),
):
    """
    A function to call the nexus writer for Tristan 10M detector.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (namedtuple): Parameters passed from the beamline.
        axes_params (BeamlineAxes): Axes for goniometer, detector and detector module.
        det_params (DetectorType): Detector definition for Tristan.
        timestamps (Tuple[str, str], optional): Collection start and end time. Defaults to None.
    """
    ecr = ExtendedRequestIO(TR.xmlfile)
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
        idx = [n for n, ax in enumerate(gonio_axes) if ax.name == k]
        gonio_axes[idx].start_pos = v[0]
    goniometer = Goniometer(gonio_axes, OSC)

    log_collection_summary(
        gonio_axes,
        scan_axis,
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
        EventFileWriter.write()
        EventFileWriter.update_timestamps(timestamps)
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )


def eiger_writer(
    master_file: Path,
    TR: namedtuple,
    axes_params: BeamlineAxes,
    det_params: DetectorType,
    timestamps: Tuple[str, str] = (None, None),
    vds_dtype: DTypeLike = np.uint16,
):
    """
    A function to call the nexus writer for Eiger 2X 4M detector.

    Args:
        master_file (Path): Path to nexus file to be written.
        TR (namedtuple): Parameters passed from the beamline.
        axes_params (BeamlineAxes): Axes for goniometer, detector and detector module.
        det_params (DetectorType): Detector definition for Eiger.
        timestamps (Tuple[str, str], optional): Collection start and end time. Defaults to (None, None).
        vds_dtype (DtypeLike): Data type for vds as np.uint##.
    """
    ecr = ExtendedRequestIO(TR.xmlfile)
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
    gonio_axes = axes_params.det_axes
    for k, v in pos.items():
        # Get correct start positions
        idx = [n for n, ax in enumerate(gonio_axes) if ax.name == k]
        gonio_axes[idx].start_pos = v[0]

    # Get scan range array
    logger.info("Calculating scan range...")
    scan_idx = [n for n, ax in enumerate(gonio_axes) if ax.name == scan_axis]

    # Define OSC scans dictionary
    OSC = calculate_scan_points(
        gonio_axes[scan_idx], rotation=True, tot_num_imgs=n_frames
    )

    goniometer = Goniometer(gonio_axes, OSC)

    log_collection_summary(
        gonio_axes,
        scan_axis,
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
        NXmx_Writer.write()
        NXmx_Writer.update_timestamps(timestamps)
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


def write_nxs(**tr_params):
    """
    Gather all parameters from the beamline and call the NeXus writers.

    Keyword Args:
        meta_file (Path | str): Path to _meta.h5 file.
        xml_file (Path | str): Path to gda-generated xml file.
        detector_name (str): Detector in use.
        exposure_time (float): Exposure time, in s.
        wavelength (float): Wavelength of incident beam, in A.
        beam_center (List[float, float]): Beam center position, in pixels.
        start_time (datetime): Experiment start time.
        stop_time (datetime): Experiment end time.
        geometry_json (Path | str): Path to GDA generated geometry json file.
        detector_json (Path | str): Path to GDA generated detector json file.
        vds_dtype (DtypeLike): Data type for vds as np.uint##.
    """
    # Get info from the beamline
    TR = tr_collect(
        meta_file=Path(tr_params["meta_file"]).expanduser().resolve(),
        xml_file=Path(tr_params["xml_file"]).expanduser().resolve(),
        detector_name=tr_params["detector_name"],
        exposure_time=tr_params["exposure_time"],
        wavelength=tr_params["wavelength"],
        beam_center=tr_params["beam_center"],
        start_time=tr_params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")  #
        if tr_params["start_time"]
        else None,  # This should be datetiem type
        stop_time=tr_params["stop_time"].strftime(
            "%Y-%m-%dT%H:%M:%S"
        )  # .strftime("%Y-%m-%dT%H:%M:%S")
        if tr_params["stop_time"]
        else None,  # idem.
        geometry_json=tr_params["geometry_json"]
        if tr_params["geometry_json"]
        else None,
        detector_json=tr_params["detector_json"]
        if tr_params["detector_json"]
        else None,
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
        from .beamline_parameters import I19_2Eiger as axes_params

        det_params = EigerDetector(
            "Eiger 2X 4M",
            (2162, 2068),
            "CdTe",
            50649,
            -1,
        )
    elif "tristan" in TR.detector_name.lower():
        from .beamline_parameters import I19_2Tristan as axes_params

        det_params = TristanDetector("Tristan 10M", (3043, 4183))
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
    timestamps = (
        get_iso_timestamp(TR.start_time),
        get_iso_timestamp(TR.stop_time),
    )

    if "tristan" in TR.detector_name:
        tristan_writer(master_file, TR, axes_params, det_params, timestamps)
    else:
        vds_dtype = (
            np.uint16 if "vds_dtype" not in tr_params.keys() else tr_params["vds_dtype"]
        )
        eiger_writer(master_file, TR, axes_params, det_params, timestamps, vds_dtype)
