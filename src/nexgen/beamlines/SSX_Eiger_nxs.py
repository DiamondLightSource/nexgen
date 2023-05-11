"""
Create a NeXus file for serial crystallography datasets collected on Eiger detector either on I19-2 or I24 beamlines.
"""
from __future__ import annotations

import logging
import math
from collections import namedtuple
from pathlib import Path

import h5py

from .. import MAX_FRAMES_PER_DATASET, log
from ..nxs_write.NexusWriter import call_writers
from ..nxs_write.NXclassWriters import write_NXdatetime, write_NXentry, write_NXnote
from ..tools.MetaReader import update_detector_axes, update_goniometer
from ..tools.VDS_tools import image_vds_writer
from ..utils import get_filename_template, get_iso_timestamp, get_nexus_filename
from . import PumpProbe, eiger_meta_links, source

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
        "start_time",
        "stop_time",
        "chip_info",
        "chipmap",
    ],
)

ssx_collect.__doc__ = """Serial collection parameters"""

# Define coordinate frame
coordinate_frame = "mcstas"

# Initialize some dictionaries
module = {}
beam = {}
attenuator = {}


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
        start_time=ssx_params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if ssx_params["start_time"]
        else None,
        stop_time=ssx_params["stop_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if ssx_params["stop_time"]
        else None,
        chip_info=ssx_params["chip_info"] if "chip_info" in ssx_params.keys() else None,
        chipmap=ssx_params["chipmap"] if "chipmap" in ssx_params.keys() else None,
    )

    visitpath = Path(visitpath).expanduser().resolve()

    # Configure logging
    logfile = visitpath / f"{beamline}_EigerSSX_nxs_writer.log"
    log.config(logfile.as_posix())

    logger.info(f"Current collection directory: {visitpath}")
    # Find metafile in directory and get info from it
    try:
        metafile = [
            f for f in visitpath.iterdir() if filename + "_meta" in f.as_posix()
        ][0]
        logger.info(f"Found {metafile} in directory.")
    except IndexError as err:
        logger.exception(err)
        logger.error(
            "Missing metadata, something might be wrong with this collection."
            "Unable to write NeXus file at this time. Please try using command line tool."
        )
        raise

    # Find datafiles
    num_files = math.ceil(SSX.num_imgs / MAX_FRAMES_PER_DATASET)
    filename_template = get_filename_template(metafile)
    filename = [filename_template % i for i in range(1, num_files + 1)]
    logger.info(f"Number of data files to be written: {len(filename)}.")

    logger.info("Creating a NeXus file for %s ..." % metafile.name)
    # Get NeXus filename
    master_file = get_nexus_filename(metafile)
    logger.info("NeXus file will be saved as %s" % master_file)

    # Get parameters depending on beamline
    logger.info(f"DLS Beamline: {beamline.upper()}.")
    if "I19" in beamline.upper():
        osc_axis = ssx_params["osc_axis"] if "osc_axis" in ssx_params.keys() else "phi"
        from .I19_2_params import eiger4M_module as module
        from .I19_2_params import eiger4M_params as detector
        from .I19_2_params import goniometer_axes as goniometer

        source["beamline_name"] = beamline.upper()
        beam["flux"] = None
    elif "I24" in beamline.upper():
        osc_axis = "omega"
        from .I24_Eiger_params import eiger9M_module as module
        from .I24_Eiger_params import eiger9M_params as detector
        from .I24_Eiger_params import goniometer_axes as goniometer

        source["beamline_name"] = beamline.upper()
        beam["flux"] = ssx_params["flux"] if "flux" in ssx_params.keys() else None
    else:
        raise ValueError(
            "Unknown beamline for SSX collections with Eiger detector."
            "Beamlines currently enabled for the writer: I24 (Eiger 9M), I19-2 (Eiger 4M)."
        )

    # Add to dictionaries
    attenuator["transmission"] = SSX.transmission

    detector["exposure_time"] = SSX.exposure_time
    detector["beam_center"] = SSX.beam_center

    # Look for wavelength
    if SSX.wavelength:
        beam["wavelength"] = SSX.wavelength
    else:
        logger.debug("No wavelength passed, looking for it in the meta file.")
        from ..tools.Metafile import DectrisMetafile

        with h5py.File(metafile, "r", libver="latest", swmr=True) as fh:
            _wl = DectrisMetafile(fh).get_wavelength()
            beam["wavelength"] = _wl

    # Look for detector distance
    with h5py.File(metafile, "r", libver="latest", swmr=True) as fh:
        update_goniometer(fh, goniometer)
        update_detector_axes(fh, detector)
    logger.debug(
        "Goniometer and detector axes have ben updated with values from the meta file."
    )
    det_z_idx = detector["axes"].index("det_z")
    if SSX.detector_distance and SSX.detector_distance != detector["starts"][det_z_idx]:
        logger.debug(
            "Detector distance value in meta file did not match with the one passed by the user.\n"
            f"Passed value: {SSX.detector_distance}; Value stored in meta file: {detector['starts'][det_z_idx]}.\n"
            "Value will be overwritten with the passed one."
        )
        detector["starts"][det_z_idx] = SSX.detector_distance

    # Get timestamps in the correct format
    timestamps = (
        get_iso_timestamp(SSX.start_time),
        get_iso_timestamp(SSX.stop_time),
    )

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

    # Define what to do based on experiment type
    if expt_type not in ["extruder", "fixed-target", "3Dgridscan"]:
        raise ValueError(
            "Please pass a valid experiment type.\n"
            "Accepted values: extruder, fixed-target, 3Dgridscan."
        )

    if expt_type == "extruder":
        from .SSX_expt import run_extruder

        goniometer, OSC, pump_info = run_extruder(goniometer, SSX.num_imgs, pump_probe)
        TRANSL = None
        tot_num_imgs = SSX.num_imgs
    elif expt_type == "fixed-target":
        # Define chipmap if needed
        chipmapfile = (
            "fullchip"
            if SSX.chipmap is None
            else Path(SSX.chipmap).expanduser().resolve()
        )
        from .SSX_expt import run_fixed_target

        # I19-2 meta file sanity check
        logger.debug(
            "Sanity check. There is no rotation here.\n"
            "Setting all rotation values to same start and end for this application."
        )
        goniometer["ends"] = [s for s in goniometer["starts"]]
        logger.debug(f"Starts: {goniometer['starts']}. Ends: {goniometer['ends']}")
        goniometer, OSC, TRANSL, pump_info = run_fixed_target(
            goniometer, SSX.chip_info, chipmapfile, pump_probe, osc_axis=osc_axis
        )
        # Check that things make sense
        if SSX.num_imgs != len(TRANSL["sam_x"]):
            logger.warning(
                f"The total number of scan points is {len(TRANSL['sam_x'])}, which does not match the total number of images passed as input {SSX.num_imgs}."
            )
            logger.warning(
                "Reset SSX.num_imgs to number of scan points for vds creation."
            )
            tot_num_imgs = len(TRANSL["sam_x"])
        else:
            tot_num_imgs = SSX.num_imgs
        tot_num_imgs = len(TRANSL["sam_x"])
    elif expt_type == "3Dgridscan":
        # Define chipmap if needed
        chipmapfile = (
            "fullchip"
            if SSX.chipmap is None
            else Path(SSX.chipmap).expanduser().resolve()
        )
        from .SSX_expt import run_3D_grid_scan

        goniometer, OSC, TRANSL, pump_info = run_3D_grid_scan(
            goniometer, SSX.chip_info, chipmapfile, pump_probe, osc_axis=osc_axis
        )
        tot_num_imgs = len(TRANSL["sam_x"])

    logger.info("--- COLLECTION SUMMARY ---")
    logger.info("Source information")
    logger.info(f"Facility: {source['name']} - {source['type']}.")
    logger.info(f"Beamline: {source['beamline_name']}")

    logger.info(f"Incident beam wavelength: {beam['wavelength']}")
    logger.info(f"Attenuation: {attenuator['transmission']}")

    logger.info("Goniometer information")
    for j in range(len(goniometer["axes"])):
        logger.info(
            f"Goniometer axis: {goniometer['axes'][j]} => {goniometer['types'][j]} on {goniometer['depends'][j]}"
        )
    logger.info(f"Oscillation axis: {list(OSC.keys())[0]}.")
    if expt_type != "extruder":
        logger.info(f"Grid scan axes: {list(TRANSL.keys())}.")

    logger.info("Detector information")
    logger.info(f"{detector['description']}")
    logger.info(
        f"Sensor made of {detector['sensor_material']} x {detector['sensor_thickness']}"
    )
    logger.info(
        f"Detector is a {detector['image_size'][::-1]} array of {detector['pixel_size']} pixels"
    )
    for k in range(len(detector["axes"])):
        logger.info(
            f"Detector axis: {detector['axes'][k]} => {detector['starts'][k]}, {detector['types'][k]} on {detector['depends'][k]}"
        )

    logger.info(f"Recorded beam center is: {detector['beam_center']}.")

    logger.info(f"Timestamps recorded: {timestamps}")

    # Get to the actual writing
    try:
        with h5py.File(master_file, "x") as nxsfile:
            write_NXentry(nxsfile)

            call_writers(
                nxsfile,
                filename,
                coordinate_frame,
                (detector["mode"], tot_num_imgs),
                goniometer,
                detector,
                module,
                source,
                beam,
                attenuator,
                OSC,
                transl_scan=TRANSL,
                metafile=metafile,
                link_list=eiger_meta_links,
            )

            if pump_status is True:
                logger.info("Write pump information to file.")
                loc = "/entry/source/notes"
                write_NXnote(nxsfile, loc, pump_info)

            # Write VDS
            # TODO discuss how VDS should be saved. All in one probably not ideal for N_EXPOSURES > 1.
            image_vds_writer(nxsfile, (int(tot_num_imgs), *detector["image_size"]))

            if timestamps:
                write_NXdatetime(nxsfile, timestamps)

            logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        raise
