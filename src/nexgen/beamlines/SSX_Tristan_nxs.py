"""
Create a NeXus file for serial crystallography datasets collected on I19-2 Tristan10M detector.
"""

import sys
import h5py
import logging

import numpy as np

from pathlib import Path
from collections import namedtuple

from .I19_2_params import goniometer_axes, tristan10M_params, source

from .. import (
    get_iso_timestamp,
    get_nexus_filename,
)

# from ..nxs_write import (
#     calculate_scan_range,
#     find_scan_axis,
# )

from ..nxs_write.NexusWriter import call_writers
from ..nxs_write.NXclassWriters import write_NXentry, write_NXnote

# Define a logger object and a formatter
logger = logging.getLogger("NeXusGenerator.I19-2_ssx")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
# Define a stream handler
CH = logging.StreamHandler(sys.stdout)
CH.setLevel(logging.DEBUG)
CH.setFormatter(formatter)
logger.addHandler(CH)

ssx_tr_collect = namedtuple(
    "ssx_collect",
    [
        "visitpath",
        "filename",
        "tot_num_X",
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
    ],
)

# Initialize dictionaries
goniometer = goniometer_axes
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
        tot_num_X=ssx_params["tot_num_X"],
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
    )
    logger.info(
        f"Start NeXus File Writer for time-resolved SSX on {source['beamline_name']}."
    )

    # Add to dictionaries
    # Detector
    detector["starts"] = [0.0, SSX_TR.detector_distance]
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
    goniometer["starts"] = goniometer["ends"] = goniometer["increments"] = [
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    ]

    # Get scan range array and rotation axis
    scan_axis = "phi"
    scan_range = (0.0, 0.0)
    # scan_axis = find_scan_axis(
    #     goniometer["axes"],
    #     goniometer["starts"],
    #     goniometer["ends"],
    #     goniometer["types"],
    # )
    # scan_idx = goniometer["axes"].index(scan_axis)
    # scan_range = calculate_scan_range(
    #     goniometer["starts"][scan_idx],
    #     goniometer["ends"][scan_idx],
    #     n_images=SSX.num_imgs,
    # )

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
        f"Detector is a {detector['image_size']} array of {detector['pixel_size']} pixels"
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
            nxentry = write_NXentry(nxsfile)

            if timestamps[0]:
                nxentry.create_dataset("start_time", data=np.string_(timestamps[0]))

            call_writers(
                nxsfile,
                [metafile],
                "mcstas",
                scan_axis,
                scan_range,
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
                metafile=metafile,  # Since there are no links, this could also be None
                link_list=None,
            )

            # TODO I'd register the number of cells like this:
            nxsfile["/entry/data"].create_dataset(
                "tot_num_cells", data=SSX_TR.tot_num_X
            )

            # Register pump status (hard coded as True)
            # TODO have pump exposure and delay also as units of time
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
                nxentry.create_dataset("end_time", data=np.string_(timestamps[1]))
            logger.info(f"{master_file} correctly written.")
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
#         tot_num_X=100,
#         beam_center=[1590.7, 1643.7],
#         det_dist=0.5,
#         start_time=datetime.now(),
#         stop_time=datetime.now(),
#         exp_time=0.002,
#         transmission=1.0,
#         wavelength=0.649,
#         pump_status=True,
#         pump_exp=3.0,
#         pump_delay=1.0,
#     )
