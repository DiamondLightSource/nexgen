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
        "chipmap",
        "chip_info",
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
ssx_tr_collect.chipmap.__doc__ = "Chipmap or block list for grid scan."
ssx_tr_collect.chip_info.__doc__ = "For a grid scan, dictionary containing basic chip information. At least it should contain: x/y_start, x/y number of blocks and block size, x/y number of steps and number of exposures."

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
        chipmap=ssx_params["chipmap"] if ssx_params["chipmap"] else None,
        chip_info=ssx_params["chip_info"] if ssx_params["chip_info"] else None,
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
                chip_info = {
                    "X_NUM_STEPS": 20,
                    "Y_NUM_STEPS": 20,
                    "X_STEP_SIZE": 0.125,
                    "Y_STEP_SIZE": 0.125,
                    "X_START": 0,
                    "Y_START": 0,
                    "Z_START": 0,
                    "X_NUM_BLOCKS": 8,
                    "Y_NUM_BLOCKS": 8,
                    "X_BLOCK_SIZE": 3.175,
                    "Y_BLOCK_SIZE": 3.175,
                }
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
#         chipmap=None,
#         chip_info=None,
#     )
