"""
Create a NeXus file for serial crystallography datasets collected on Tristan10M detector either on I19-2 or I24 beamlines.
"""

import logging
from collections import namedtuple
from pathlib import Path

import h5py

from .. import log
from ..nxs_write.NexusWriter import call_writers
from ..nxs_write.NXclassWriters import write_NXdatetime, write_NXentry, write_NXnote
from ..utils import get_iso_timestamp, get_nexus_filename
from . import source
from .I19_2_params import tristan10M_module as module
from .I19_2_params import tristan10M_params as detector

__all__ = ["ssx_tristan_writer"]

# Define a logger object and a formatter
logger = logging.getLogger("nexgen.SSX_Tristan")

ssx_tr_collect = namedtuple(
    "ssx_collect",
    [
        "exposure_time",
        "detector_distance",
        "beam_center",
        "transmission",
        "wavelength",
        "start_time",
        "stop_time",
        "chipmap",
        "chip_info",
    ],
)

ssx_tr_collect.__doc__ = (
    """Parameters that define a serial collection using a Tristan detector."""
)

# Define coordinate frame
coordinate_frame = "mcstas"

# Initialize dictionaries
beam = {}
attenuator = {}


def ssx_tristan_writer(
    visitpath: Path | str,
    filename: str,
    beamline: str,
    **ssx_params,
):
    """
    Gather all parameters from the beamline and call the NeXus writers.

    Args:
        visitpath (Path | str): Path to colection directory.
        filename (str): Root of the filename.
        beamline (str): Beamline on which the experiment is being run.

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
    """
    # Get info from the beamline
    SSX_TR = ssx_tr_collect(
        exposure_time=float(ssx_params["exp_time"]),
        detector_distance=float(ssx_params["det_dist"]),
        beam_center=ssx_params["beam_center"],
        transmission=float(ssx_params["transmission"]),
        wavelength=float(ssx_params["wavelength"]),
        start_time=ssx_params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if ssx_params["start_time"]
        else None,  # This should be datetiem type
        stop_time=ssx_params["stop_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if ssx_params["stop_time"]
        else None,  # idem.
        chipmap=ssx_params["chipmap"] if ssx_params["chipmap"] else None,
        chip_info=ssx_params["chip_info"] if ssx_params["chip_info"] else None,
    )

    visitpath = Path(visitpath).expanduser().resolve()
    filename = ssx_params["filename"]

    logfile = SSX_TR.visitpath / f"{beamline}_TristanSSX_nxs_writer.log"
    # Configure logging
    log.config(logfile.as_posix())

    logger.info(
        f"Start NeXus File Writer for time-resolved SSX on beamline {beamline} at DLS."
    )

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

    # Add some information to logger
    logger.info("Creating a NeXus file for %s ..." % metafile.name)
    # Get NeXus filename
    master_file = get_nexus_filename(metafile)
    logger.info("NeXus file will be saved as %s" % master_file)

    # Get parameters depending on beamline
    logger.info(f"DLS Beamline: {beamline.upper()}.")
    if "I19" in beamline.upper():
        from .I19_2_params import goniometer_axes as goniometer

        source["beamline_name"] = beamline.upper()
        beam["flux"] = None
    elif "I24" in beamline.upper():
        from .I24_Eiger_params import goniometer_axes as goniometer

        source["beamline_name"] = beamline.upper()
        beam["flux"] = ssx_params["flux"] if "flux" in ssx_params.keys() else None
    else:
        raise ValueError(
            "Unknown beamline for SSX collections with Tristan 10M detector."
            "Beamlines currently enabled for the writer: I24, I19-2."
        )

    # Add to dictionaries
    # Detector
    # If location is I24, two_theta is not present
    detector["starts"] = (
        [0.0, SSX_TR.detector_distance]
        if "I19" in beamline.upper()
        else [SSX_TR.detector_distance]
    )
    if "I24" in beamline.upper():
        detector["axes"] = ["det_z"]
        detector["types"] = ["translation"]
        detector["units"] = ["mm"]
        detector["depends"] = ["."]
        detector["vectors"] = [0, 0, 1]
        detector["increments"] = [0.0]

    detector["exposure_time"] = SSX_TR.exposure_time
    detector["beam_center"] = SSX_TR.beam_center

    # Attenuator
    attenuator["transmission"] = SSX_TR.transmission

    # Beam
    beam["wavelength"] = SSX_TR.wavelength

    l = len(goniometer["axes"])
    goniometer["starts"] = goniometer["ends"] = goniometer["increments"] = l * [0.0]

    # Get rotation scan range array and axis
    osc_axis = "phi" if "I19" in SSX_TR.location else "omega"
    osc_range = (0.0, 0.0)

    OSC = {osc_axis: osc_range}

    # Get timestamps in the correct format
    timestamps = (
        get_iso_timestamp(SSX_TR.start_time),
        get_iso_timestamp(SSX_TR.stop_time),
    )

    logger.info("--- COLLECTION SUMMARY ---")
    logger.info("Source information")
    logger.info(f"Facility: {source['name']} - {source['type']}.")
    logger.info(f"Beamline: {source['beamline_name']}")

    logger.info(f"Incident beam wavelength: {beam['wavelength']}")
    logger.info(f"Attenuation: {attenuator['transmission']}")

    logger.info("Goniometer information")
    for j in range(len(goniometer["axes"])):
        logger.info(
            f"Goniometer axis: {goniometer['axes'][j]} => {goniometer['starts'][j]}, {goniometer['types'][j]} on {goniometer['depends'][j]}"
        )
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

    logger.info(f"Timestamps recorded: {timestamps}.")

    try:
        with h5py.File(master_file, "x") as nxsfile:
            write_NXentry(nxsfile)

            if timestamps[0]:
                write_NXdatetime(nxsfile, (timestamps[0], None))

            call_writers(
                nxsfile,
                [metafile],
                coordinate_frame,
                (
                    detector["mode"],
                    None,
                ),  # since it's event mode, don't need event number or chunk number here
                goniometer,
                detector,
                module,
                source,
                beam,
                attenuator,
                OSC,
                transl_scan=None,
                metafile=metafile,  # Since there are no links, this could also be None
                link_list=None,
            )

            # Save chipmap (list of city blocks)
            if SSX_TR.chipmap:
                # Assuming 8x8 fast chip
                from .SSX_chip import read_chip_map

                chip = read_chip_map(SSX_TR.chipmap, 8, 8)
                mapping = {"chipmap": str(chip)}
                logger.info(
                    f"Chipmap read from {SSX_TR.chipmap}, saving in '/entry/source/notes/chipmap'."
                )
                write_NXnote(nxsfile, "/entry/source/notes/", mapping)
                # To read this: eval(dset[()])
            # Save chip info if passed. If not save I24-like chip info plus warning message
            logger.info("Save chip information in /entry/source/notes/chip")
            if SSX_TR.chip_info:
                # Make chip info more readable
                chip_info = {k: v[1] for k, v in SSX_TR.chip_info.items()}
                chipdef = {"chip": str(chip_info)}
                write_NXnote(nxsfile, "/entry/source/notes/", chipdef)
            else:
                logger.warning(
                    f"Dictionary containing chip info was not passed to the writer."
                    "The following values will be written as default: "
                    "x/y_num_blocks = 8 \n x/y_block_size = 3.175 \n x/y_num_steps = 20 \n x/y_step_size = 0.125"
                )
                from .SSX_chip import CHIP_DICT_DEFAULT as chip_info

                chipdef = {"chip": str(chip_info)}
                write_NXnote(nxsfile, "/entry/source/notes", chipdef)

            if timestamps[1]:
                write_NXdatetime(nxsfile, (None, timestamps[1]))
            logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        raise
