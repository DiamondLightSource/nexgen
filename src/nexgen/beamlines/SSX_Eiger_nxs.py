"""
Create a NeXus file for serial crystallography datasets collected on Eiger detector either on I19-2 or I24 beamlines.
"""
from __future__ import annotations

"""
Create a NeXus file for serial crystallography datasets collected on Eiger detector either on I19-2 or I24 beamlines.
"""

import logging
from collections import namedtuple
from pathlib import Path

import h5py

from .. import log
from ..nxs_utils import Attenuator, Beam, Detector, EigerDetector, Goniometer, Source
from ..nxs_write.NXmxWriter import NXmxFileWriter
from ..tools.MetaReader import define_vds_data_type, update_axes_from_meta
from ..utils import get_iso_timestamp
from . import PumpProbe

__all__ = ["ssx_eiger_writer"]

# Define logger
logger = logging.getLogger("nexgen.SSX_Eiger")

# Define a namedtuple for collection parameters
ssx_collect = namedtuple(
    "ssx_collect",
    [
        "num_imgs",
        "exposure_time",
        "detector_distance",
        "beam_center",
        "transmission",
        "wavelength",
        "flux",
        "start_time",
        "stop_time",
        "chip_info",
        "chipmap",
    ],
)

ssx_collect.__doc__ = """Serial collection parameters"""


def ssx_eiger_writer(
    visitpath: Path | str,
    filename: str,
    beamline: str,
    num_imgs: int,
    expt_type: str = "fixed-target",
    pump_status: bool = False,
    **ssx_params,
):
    """Gather all collection parameters and write the NeXus file for SSX using Eiger detector.

    Args:
        visitpath (Path | str): Collection directory.
        filename (str): Filename root.
        beamline (str): Beamline on which the experiment is being run.
        num_imgs (int): Total number of images collected.
        expt_type (str, optional): Experiment type, accepted values: extruder,
            fixed-target, 3Dgridscan. Defaults to "fixed-target".
        pump_status (bool, optional): True for pump-probe experiment. Defaults to False.

    Keyword Args:
        exp_time (float): Exposure time, in s.
        det_dist (float): Distance between sample and detector, in mm.
        beam_center (List[float, float]): Beam center position, in pixels.
        transmission (float): Attenuator transmission, in %.
        wavelength (float): Wavelength of incident beam, in A.
        flux (float): Total flux.
        start_time (datetime): Experiment start time.
        stop_time (datetime): Experiment end time.
        chip_info (Dict): For a grid scan, dictionary containing basic chip information.
            At least it should contain: x/y_start, x/y number of blocks and block size, x/y number of steps and number of exposures.
        chipmap (Path | str): Path to the chipmap file corresponding to the experiment,
            or 'fullchip' indicating that the whole chip is being scanned.
        pump_exp (float): Pump exposure time, in s.
        pump_delay (float): Pump delay time, in s.
        osc_axis (str): Oscillation axis. Always omega on I24. If not passed it will default to phi for I19-2.

    Raises:
        ValueError: If an invalid beamline name is passed.
        ValueError: If an invalid experiment type is passed.
    """
    SSX = ssx_collect(
        num_imgs=int(num_imgs),
        exposure_time=ssx_params["exp_time"],
        detector_distance=ssx_params["det_dist"]
        if "det_dist" in ssx_params.keys()
        else None,
        beam_center=ssx_params["beam_center"],
        transmission=ssx_params["transmission"]
        if "transmission" in ssx_params.keys()
        else None,
        wavelength=ssx_params["wavelength"]
        if "wavelength" in ssx_params.keys()
        else None,
        flux=ssx_params["flux"] if "flux" in ssx_params.keys() else None,
        start_time=ssx_params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if ssx_params["start_time"]
        else None,
        stop_time=ssx_params["stop_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if ssx_params["stop_time"]
        else None,
        chip_info=ssx_params["chip_info"] if "chip_info" in ssx_params.keys() else None,
        chipmap=ssx_params["chipmap"] if "chipmap" in ssx_params.keys() else None,
    )

    if expt_type.lower() not in ["extruder", "fixed-target", "3Dgridscan"]:
        raise ValueError("Unknown experiment type.")

    visitpath = Path(visitpath).expanduser().resolve()

    # Configure logging
    logfile = visitpath / f"{beamline}_EigerSSX_nxs_writer.log"
    log.config(logfile.as_posix())

    logger.info(f"Current collection directory: {visitpath}")
    # Get NeXus filename
    master_file = visitpath / f"{filename}.nxs"
    logger.info("NeXus file will be saved as %s" % master_file)

    # Get parameters depending on beamline
    logger.info(f"DLS Beamline: {beamline.upper()}.")
    if "I19" in beamline.upper():
        source = Source("I19-2")
        osc_axis = ssx_params["osc_axis"] if "osc_axis" in ssx_params.keys() else "phi"
        from .beamline_parameters import I19_2Eiger as axes_params

        eiger_params = EigerDetector(
            "Eiger 2X 4M",
            (2162, 2068),
            "CdTe",
            50649,
            -1,
        )
    elif "I24" in beamline.upper():
        source = Source("I24")
        osc_axis = "omega"
        from .beamline_parameters import I24Eiger as axes_params

        eiger_params = EigerDetector(
            "Eiger 2X 9M",
            (3262, 3108),
            "CdTe",
            50649,
            -1,
        )
    else:
        raise ValueError(
            "Unknown beamline for SSX collections with Eiger detector."
            "Beamlines currently enabled for the writer: I24 (Eiger 9M), I19-2 (Eiger 4M)."
        )

    # Define what to do based on experiment type
    if expt_type not in ["extruder", "fixed-target", "3Dgridscan"]:
        raise ValueError(
            "Please pass a valid experiment type.\n"
            "Accepted values: extruder, fixed-target, 3Dgridscan."
        )
    logger.info(f"Running {expt_type} collection.")

    # Get pump information
    pump_probe = PumpProbe()
    if pump_status is True:
        # Exposure and delay could also be found in dictionary for grid scan
        logger.info("Pump status is True.")
        pump_probe.status = pump_status
        pump_probe.exposure = (
            ssx_params["pump_exp"] if "pump_exp" in ssx_params.keys() else None
        )
        pump_probe.delay = (
            ssx_params["pump_exp"] if "pump_exp" in ssx_params.keys() else None
        )

        logger.info(f"Recorded pump exposure time: {pump_probe.exposure}")
        logger.info(f"Recorded pump delay time: {pump_probe.delay}")

    # Get timestamps in the correct format
    timestamps = (
        get_iso_timestamp(SSX.start_time),
        get_iso_timestamp(SSX.stop_time),
    )

    # Find metafile in directory and get info from it
    try:
        metafile = [
            f for f in visitpath.iterdir() if filename + "_meta" in f.as_posix()
        ][0]
        logger.debug(f"Found {metafile} in directory.")
    except IndexError as err:
        logger.exception(err)
        logger.error(
            "Missing metadata, something might be wrong with this collection."
            "Unable to write NeXus file at this time. Please try using command line tool."
        )
        raise

    # Define Attenuator
    attenuator = Attenuator(SSX.transmission)
    # Define Beam
    wl = SSX.wavelength
    if not wl:
        logger.debug("No wavelength passed, looking for it in the meta file.")
        from ..tools.Metafile import DectrisMetafile

        with h5py.File(metafile, "r", libver="latest", swmr=True) as fh:
            wl = DectrisMetafile(fh).get_wavelength()
    beam = Beam(wl, SSX.flux)

    # Define Goniometer axes
    gonio_axes = axes_params.gonio
    # Define Detector
    det_axes = axes_params.det_axes

    # Update axes starts and get data type from meta file
    with h5py.File(metafile, "r", libver="latest", swmr=True) as fh:
        meta = DectrisMetafile(fh)
        vds_dtype = define_vds_data_type(meta)
        update_axes_from_meta(meta, gonio_axes, osc_axis=osc_axis)
        update_axes_from_meta(meta, det_axes)

    logger.debug(
        "Goniometer and detector axes have ben updated with values from the meta file."
    )

    # TODO add check on det_z vs SSX.det_dist here

    # Define detector
    detector = Detector(
        eiger_params,
        det_axes,
        SSX.beam_center,
        SSX.exposure_time,
        [axes_params.fast_axis, axes_params.slow_axis],
    )

    # TODO
    if expt_type == "extruder":
        print("ext")
        OSC = {}
        TRANSL = None
        pump_info = pump_probe.to_dict()  # to be returned by run func
    elif expt_type == "fixed-target":
        print("ft")
        OSC = {}
        TRANSL = {}
        pump_info = pump_probe.to_dict()
    else:
        print("3D")
        OSC = {}
        TRANSL = {}
        pump_info = pump_probe.to_dict()

    # TODO sanity check overwriting num_imaeges
    tot_num_imgs = SSX.num_imgs

    # TODO
    # Define goniometer - only after expt call
    goniometer = Goniometer(gonio_axes)

    # Log a bunch of stuff
    logger.info("--- COLLECTION SUMMARY ---")
    logger.info("Source information")
    logger.info(f"Facility: {source.name} - {source.facility_type}.")
    logger.info(f"Beamline: {source.beamline}")

    logger.info(f"Incident beam wavelength: {beam.wavelength}")
    logger.info(f"Attenuation: {attenuator.transmission}")

    logger.info("Goniometer information")
    for ax in gonio_axes:
        logger.info(
            f"Goniometer axis: {ax.name} => {ax.transformation_type} on {ax.depends}"
        )
    logger.info(f"Oscillation axis: {list(OSC.keys())[0]}.")
    if expt_type != "extruder":
        logger.info(f"Grid scan axes: {list(TRANSL.keys())}.")

    logger.info("Detector information")
    logger.info(f"{detector.detector_params.description}")
    logger.info(
        f"Sensor made of {detector.detector_params.sensor_material} x {detector.detector_params.sensor_thickness}"
    )
    logger.info(
        f"Detector is a {detector.detector_params.image_size[::-1]} array of {detector.detector_params.pixel_size} pixels"
    )
    for ax in detector.detector_axes:
        logger.info(
            f"Detector axis: {ax.name} => {ax.start_pos}, {ax.transformation_type} on {ax.depends}"
        )

    logger.info(f"Recorded beam center is: {detector.beam_center}.")
    logger.info(f"Exposure time: {detector.exp_time} s.")

    logger.info(f"Timestamps recorded: {timestamps}")

    # Get to the actual writing
    try:
        NXmx_Writer = NXmxFileWriter(
            master_file,
            goniometer,
            detector,
            source,
            beam,
            attenuator,
            tot_num_imgs,
        )
        NXmx_Writer.write(start_time=timestamps[0])
        if pump_status is True:
            logger.info("Write pump information to file.")
            NXmx_Writer.update_timestamps(
                notes=pump_info,
                loc="/entry/source/notes",
            )
        NXmx_Writer.write_vds(
            vds_shape=(tot_num_imgs, *detector.detector_params.image_size),
            vds_dtype=vds_dtype,
        )
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        raise
