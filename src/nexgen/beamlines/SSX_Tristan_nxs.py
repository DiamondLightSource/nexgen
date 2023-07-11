"""
Create a NeXus file for serial crystallography datasets collected on Tristan10M detector either on I19-2 or I24 beamlines.
"""
from __future__ import annotations

import logging
from collections import namedtuple
from pathlib import Path

from .. import log
from ..nxs_utils import Attenuator, Beam, Detector, Goniometer, Source, TristanDetector
from ..nxs_write.NXmxWriter import EventNXmxFileWriter
from ..utils import Point3D, get_iso_timestamp
from .beamline_utils import collection_summary_log

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

    logger.info(f"Current collection directory: {visitpath.as_posix()}")
    # Get NeXus filename
    master_file = visitpath / f"{filename}.nxs"
    logger.info("NeXus file will be saved as %s" % master_file.as_posix())

    # Check if metafile in directory.
    try:
        metafile = [
            f for f in visitpath.iterdir() if filename + "_meta" in f.as_posix()
        ][0]
        logger.info(f"Found {metafile} in directory.")
    except IndexError:
        logger.warning(
            "Missing metadata file at this time, something might be wrong with this collection."
            f"The hard link to {filename}_meta.h5 will most likely be broken."
        )

    # Get parameters depending on beamline
    logger.info(f"DLS Beamline: {beamline.upper()}.")
    if "I19" in beamline.upper():
        source = Source("I19-2")
        from .beamline_utils import I19_2Tristan as axes_params

    elif "I24" in beamline.upper():
        source = Source("I19-2")
        from .beamline_utils import I24Eiger as axes_params

        axes_params.fast_axis = Point3D(-1, 0, 0)
        axes_params.slow_axis = Point3D(0, 1, 0)

    else:
        raise ValueError(
            "Unknown beamline for SSX collections with Tristan 10M detector."
            "Beamlines currently enabled for the writer: I24, I19-2."
        )

    # Define Attenuator
    attenuator = Attenuator(SSX_TR.transmission)
    # Define Beam
    wl = SSX_TR.wavelength
    flux = ssx_params["flux"] if "flux" in ssx_params.keys() else None
    beam = Beam(wl, flux)

    # Define Detector axes
    det_axes = axes_params.det_axes

    # Define Detector
    tristan_params = TristanDetector("Tristan 10M", (3043, 4183))
    if "I19" in beamline.upper():
        det_axes[0].start_pos = 0.0  # two_theta
        det_axes[1].start_pos = SSX_TR.detector_distance  # det_z
    else:
        # Only det_z for detector axes
        det_axes[0].start_pos = SSX_TR.detector_distance

    detector = Detector(
        tristan_params,
        det_axes,
        SSX_TR.beam_center,
        SSX_TR.exposure_time,
        [axes_params.fast_axis, axes_params.slow_axis],
    )

    # Define Goniometer axes
    gonio_axes = axes_params.gonio

    # Get rotation scan range array and axis
    osc_axis = "phi" if "I19" in SSX_TR.location else "omega"
    osc_range = (0.0, 0.0)

    OSC = {osc_axis: osc_range}

    # Define Goniometer
    goniometer = Goniometer(gonio_axes, OSC)

    # Get timestamps in the correct format
    timestamps = (
        get_iso_timestamp(SSX_TR.start_time),
        get_iso_timestamp(SSX_TR.stop_time),
    )

    collection_summary_log(
        logger,
        gonio_axes,
        ["sam_y", "sam_x"],
        detector,
        attenuator,
        beam,
        source,
        timestamps,
    )

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

        # Save chipmap (list of city blocks)
        if SSX_TR.chipmap:
            # Assuming 8x8 fast chip
            from .SSX_chip import read_chip_map

            chip = read_chip_map(SSX_TR.chipmap, 8, 8)
            mapping = {"chipmap": str(chip)}
            logger.info(
                f"Chipmap read from {SSX_TR.chipmap}, saving in '/entry/source/notes/chipmap'."
            )
            EventFileWriter.add_NXnote(mapping, "/entry/source/notes/")
            # To read this: eval(dset[()])

        # Save chip info if passed. If not save I24-like chip info plus warning message
        logger.info("Save chip information in /entry/source/notes/chip")
        if SSX_TR.chip_info:
            # Make chip info more readable
            chip_info = {k: v[1] for k, v in SSX_TR.chip_info.items()}
            chipdef = {"chip": str(chip_info)}
            EventFileWriter.add_NXnote(chipdef, "/entry/source/notes/")
        else:
            logger.warning(
                "Dictionary containing chip info was not passed to the writer."
                "The following values will be written as default: "
                "x/y_num_blocks = 8 \n x/y_block_size = 3.175 \n x/y_num_steps = 20 \n x/y_step_size = 0.125"
            )
            from .SSX_chip import CHIP_DICT_DEFAULT as chip_info

            chipdef = {"chip": str(chip_info)}
            EventFileWriter.add_NXnote(chipdef, "/entry/source/notes/")

            logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        raise
