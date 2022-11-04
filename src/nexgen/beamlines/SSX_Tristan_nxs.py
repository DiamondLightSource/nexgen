"""
Create a NeXus file for serial crystallography datasets collected on Tristan10M detector either on I19-2 or I24 beamlines.
"""

import logging
from collections import namedtuple
from pathlib import Path

import h5py

from .. import get_iso_timestamp, get_nexus_filename, log
from ..nxs_write.NexusWriter import call_writers
from ..nxs_write.NXclassWriters import write_NXdatetime, write_NXentry, write_NXnote
from .I19_2_params import source, tristan10M_params

# Define a logger object and a formatter
logger = logging.getLogger("nexgen.I19-2_ssx")

# TODO Change tot_num_X to current chip map, or just the list of blocks. The list of blocks should go in a NXnote.
# TODO Might need to also have I24 geometry in here
ssx_tr_collect = namedtuple(
    "ssx_collect",
    [
        "visitpath",
        "filename",
        "location",
        "beam_center",
        "detector_distance",
        "start_time",
        "stop_time",
        "exposure_time",
        "transmission",
        "wavelength",
        "pump_status",
        "pump_exp",
        "pump_delay",
        "chipmap",
    ],
)

ssx_tr_collect.__doc__ = (
    """Parameters that define a serial collection using a Tristan detector."""
)
ssx_tr_collect.visitpath.__doc__ = "Path to colection directory."
ssx_tr_collect.filename.__doc__ = "Root of the filename."
ssx_tr_collect.location.__doc__ = "Beamline on which the experiment is being run."
ssx_tr_collect.beam_center.__doc__ = "Beam center position, in pixels."
ssx_tr_collect.detector_distance.__doc__ = (
    "Distance between sample and detector, in mm."
)
ssx_tr_collect.start_time.__doc__ = "Experiment start time."
ssx_tr_collect.stop_time.__doc__ = "Experiment end time."
ssx_tr_collect.exposure_time.__doc__ = "Exposure time, in s."
ssx_tr_collect.transmission.__doc__ = "Attenuator transmission, in %."
ssx_tr_collect.wavelength.__doc__ = "Wavelength of incident beam."
ssx_tr_collect.pump_status.__doc__ = (
    "True for a pump-probe experiment, false otherwise."
)
ssx_tr_collect.pump_exp.__doc__ = "Pump exposure time, in s."
ssx_tr_collect.pump_delay.__doc__ = "Pump delay time, in s."
ssx_tr_collect.chipmap.__doc__ = "Chipmap or block list for grid scan."

# Define coordinate frame
coordinate_frame = "mcstas"

# Initialize dictionaries
goniometer = {}
detector = tristan10M_params
module = {}
beam = {}
attenuator = {}


def write_nxs(**ssx_params):
    """
    Gather all parameters from the beamline and call the NeXus writers.
    """
    # Get info from the beamline
    SSX_TR = ssx_tr_collect(
        visitpath=Path(ssx_params["visitpath"]).expanduser().resolve(),
        filename=ssx_params["filename"],
        location=ssx_params["location"],
        beam_center=ssx_params["beam_center"],
        detector_distance=ssx_params["det_dist"],
        start_time=ssx_params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if ssx_params["start_time"]
        else None,  # This should be datetiem type
        stop_time=ssx_params["stop_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if ssx_params["stop_time"]
        else None,  # idem.
        exposure_time=ssx_params["exp_time"],
        transmission=ssx_params["transmission"],
        wavelength=ssx_params["wavelength"],
        pump_status=True,
        pump_exp=ssx_params["pump_exp"],
        pump_delay=ssx_params["pump_delay"],
        chipmap=ssx_params["chipmap"] if ssx_params["chipmap"] else None,
    )

    logfile = SSX_TR.visitpath / "TristanSSX_nxs_writer.log"
    # Configure logging
    log.config(logfile.as_posix())

    logger.info(
        f"Start NeXus File Writer for time-resolved SSX on beamline {source['beamline_name']} at DLS."
    )

    # Add to dictionaries
    # Detector
    # If location is I24, two_theta is not present
    detector["starts"] = (
        [0.0, SSX_TR.detector_distance]
        if "I19" in SSX_TR.location
        else [SSX_TR.detector_distance]
    )
    if "I24" in SSX_TR.location:
        detector["axes"] = ["det_z"]
        detector["types"] = ["translation"]
        detector["units"] = ["mm"]
        detector["depends"] = ["."]
        detector["vectors"] = [0, 0, 1]
        detector["increments"] = [0.0]
    detector["exposure_time"] = SSX_TR.exposure_time
    detector["beam_center"] = SSX_TR.beam_center

    # Module
    module["fast_axis"] = detector.pop("fast_axis")
    module["slow_axis"] = detector.pop("slow_axis")
    # goniometer, detector, module = read_params_from_json()
    # Set value for module_offset calculation.
    module["module_offset"] = "1"

    # Attenuator
    attenuator["transmission"] = SSX_TR.transmission

    # Beam
    beam["wavelength"] = SSX_TR.wavelength
    beam["flux"] = None

    # Goniometer
    if "I19" in SSX_TR.location:
        from .I19_2_params import goniometer_axes
    elif "I24" in SSX_TR.location:
        from .I24_Eiger_params import goniometer_axes

    for k, v in goniometer_axes.items():
        goniometer[k] = v

    l = len(goniometer["axes"])
    goniometer["starts"] = goniometer["ends"] = goniometer["increments"] = l * [0.0]

    # Get rotation scan range array and axis
    osc_axis = "phi" if "I19" in SSX_TR.location else "omega"
    osc_range = (0.0, 0.0)

    OSC = {osc_axis: osc_range}

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

    # Get timestamps in the correct format
    timestamps = (
        get_iso_timestamp(SSX_TR.start_time),
        get_iso_timestamp(SSX_TR.stop_time),
    )
    logger.info(f"Timestamps recorded: {timestamps}")

    logger.info(f"Current collection directory: {SSX_TR.visitpath}")
    # Find metafile in directory and get info from it
    metafile = [
        f
        for f in SSX_TR.visitpath.iterdir()
        if SSX_TR.filename + "_meta" in f.as_posix()
    ][0]
    logger.info(f"Found {metafile} in directory.")

    # Add some information to logger
    logger.info("Creating a NeXus file for %s ..." % metafile.name)
    # Get NeXus filename
    master_file = get_nexus_filename(metafile)
    logger.info("NeXus file will be saved as %s" % master_file)

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
                nxsfile.create_dataset("/entry/data/chipmap", data=str(chip))
                # To read this: eval(dset[()])
                # Instead of saving chipmap location read file and save dictionary.
                # TODO add part to copy functions to get the positions.

            # Register pump status (hard coded as True)
            pump_info = {"pump_status": True}
            logger.info("Add pump information.")
            if SSX_TR.pump_exp:
                pump_info["pump_exposure_time"] = SSX_TR.pump_exp
                logger.info(f"Recorded pump exposure time: {SSX_TR.pump_exp}")
            else:
                pump_info["pump_exposure_time"] = None
                logger.warning(
                    "Pump exposure time has not been recorded and won't be written to file."
                )
            if SSX_TR.pump_delay:
                pump_info["pump_delay"] = SSX_TR.pump_delay
                logger.info(f"Recorded pump delay time: {SSX_TR.pump_delay}")
            else:
                pump_info["pump_delay"] = None
                logger.warning(
                    "Pump delay has not been recorded and won't be written to file."
                )
            write_NXnote(nxsfile, "/entry/source/notes", pump_info)

            if timestamps[1]:
                write_NXdatetime(nxsfile, (None, timestamps[1]))
            logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )


# # Example usage
# if __name__ == "__main__":
#     from datetime import datetime

#     write_nxs(
#         visitpath=sys.argv[1],
#         filename=sys.argv[2],
#         location="I19",
#         beam_center=[1590.7, 1643.7],
#         det_dist=0.5,
#         start_time=datetime.now(),
#         stop_time=None,
#         exp_time=0.002,
#         transmission=1.0,
#         wavelength=0.649,
#         pump_status=True,
#         pump_exp=3.0,
#         pump_delay=1.0,
#         chipmap=None,
#     )
