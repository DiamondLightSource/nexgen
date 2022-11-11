"""
Create a NeXus file for serial crystallography datasets collected on I24 Eiger 2X 9M detector.
"""
from __future__ import annotations

import glob
import logging
from collections import namedtuple
from pathlib import Path
from typing import Dict, List, Tuple

import h5py
import numpy as np

from .. import get_iso_timestamp, get_nexus_filename, log
from ..nxs_write.NexusWriter import ScanReader, call_writers
from ..nxs_write.NXclassWriters import write_NXdatetime, write_NXentry, write_NXnote
from ..tools.VDS_tools import image_vds_writer
from .I24_Eiger_params import dset_links, eiger9M_params, goniometer_axes, source
from .SSX_chip import Chip, compute_goniometer, read_chip_map

# Define a logger object and a formatter
logger = logging.getLogger("nexgen.I24")

ssx_collect = namedtuple(
    "ssx_collect",
    [
        "visitpath",
        "filename",
        "exp_type",
        "num_imgs",
        "beam_center",
        "detector_distance",
        "start_time",
        "stop_time",
        "exposure_time",
        "transmission",
        "wavelength",
        "flux",
        "pump_status",
        "pump_exp",
        "pump_delay",
        "chip_info",
        "chipmap",
    ],
)

ssx_collect.__doc__ = """Parameters that define a serial collection on I24."""
ssx_collect.visitpath.__doc__ = "Path to colection directory."
ssx_collect.filename.__doc__ = "Root of the filename."
ssx_collect.exp_type.__doc__ = (
    "Experiment being run. Accepted values for I24: extruder, fixed_target, 3Dgridscan."
)
ssx_collect.num_imgs.__doc__ = "Total number of images collected."
ssx_collect.beam_center.__doc__ = "Beam center position, in pixels."
ssx_collect.detector_distance.__doc__ = "Distance between sample and detector, in mm."
ssx_collect.start_time.__doc__ = "Experiment start time."
ssx_collect.stop_time.__doc__ = "Experiment end time."
ssx_collect.exposure_time.__doc__ = "Exposure time, in s."
ssx_collect.transmission.__doc__ = "Attenuator transmission, in %."
ssx_collect.wavelength.__doc__ = "Wavelength of incident beam."
ssx_collect.flux.__doc__ = "Total flux."
ssx_collect.pump_status.__doc__ = "True for a pump-probe experiment, false otherwise."
ssx_collect.pump_exp.__doc__ = "Pump exposure time, in s."
ssx_collect.pump_delay.__doc__ = "Pump delay time, in s."
ssx_collect.chip_info.__doc__ = "For a grid scan, dictionary containing basic chip information. At least it should contain: x/y_start, x/y number of blocks and block size, x/y number of steps and number of exposures."
ssx_collect.chipmap.__doc__ = (
    "Path to the chipmap file corresponding to the experiment."
)

# Define coordinate frame
coordinate_frame = "mcstas"

# Initialize dictionaries
goniometer = goniometer_axes
detector = eiger9M_params
module = {}
beam = {}
attenuator = {}

#
def extruder(
    master_file: Path,
    filename: List[Path],
    num_imgs: int,
    metafile: Path = None,  # Just in case meta is not generated for some reason
    timestamps: Tuple[str] = None,
    pump_info: Dict = None,
):
    """
    Write the NeXus file for extruder collections, pump-probe and not.

    Args:
        master_file (Path): Path to the NeXus file to be written.
        filename (List[Path]): List of paths to data files.
        num_imgs (int): Total number of images passed as a beamline parameter.
        metafile (Path, optional): Path to the Dectris _meta.h5 file. Deafults to None.
        timestamps (Tuple[str], optional): Start and end time of data collection, if known. Defaults to None.
        pump_info (Dict, optional): Details of a pump probe experiment eg. pump exposure time, pump delay, etc. Defaults to None.
    """
    logger.info("Write NeXus file for extruder.")

    goniometer["starts"] = goniometer["ends"] = goniometer["increments"] = [
        0.0,
        0.0,
        0.0,
        0.0,
    ]

    # Get scan range array and rotation axis
    OSC, TRANSL = ScanReader(goniometer, n_images=int(num_imgs))
    del TRANSL

    logger.info("Goniometer information")
    for j in range(len(goniometer["axes"])):
        logger.info(
            f"Goniometer axis: {goniometer['axes'][j]} => {goniometer['starts'][j]}, {goniometer['types'][j]} on {goniometer['depends'][j]}"
        )

    try:
        with h5py.File(master_file, "x") as nxsfile:
            write_NXentry(nxsfile)

            call_writers(
                nxsfile,
                filename,
                coordinate_frame,
                (detector["mode"], num_imgs),
                goniometer,
                detector,
                module,
                source,
                beam,
                attenuator,
                OSC,
                transl_scan=None,
                metafile=metafile,
                link_list=dset_links,
            )

            # Write pump-probe information if requested
            if pump_info:
                logger.info("Write pump information to file.")
                if pump_info["pump_exposure_time"] is None:
                    logger.warning(
                        "Pump exposure time has not been recorded and won't be written to file."
                    )
                if pump_info["pump_delay"] is None:
                    logger.warning(
                        "Pump delay has not been recorded and won't be written to file."
                    )
                loc = "/entry/source/notes"
                write_NXnote(nxsfile, loc, pump_info)

            # Write VDS
            image_vds_writer(nxsfile, (int(num_imgs), *detector["image_size"]))

            if timestamps:
                write_NXdatetime(nxsfile, timestamps)

            logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )


def fixed_target(
    master_file: Path,
    filename: List[Path],
    num_imgs: int,
    chip_info: Dict,
    chipmap: Path | str,
    metafile: Path = None,
    timestamps: Tuple[str] = None,
    pump_info: Dict = None,
):
    """
    Write the NeXus file for fixed target collections, pump probe and not.

    Args:
        master_file (Path): Path to the NeXus file to be written.
        filename (List[Path]):  List of paths to file.
        num_imgs (int): Total number of images passed as a beamline parameter.
        chip_info (Dict): Basic information about the chip in use and collection dynamics.
        chipmap (Path | str): Path to the chipmap file corresponding to the current collection.
        metafile (Path, optional):  Path to the _meta.h5 file. Defaults to None.
        timestamps (Tuple[str], optional): Start and end time of data collection, if known. See docs for accepted formats. Defaults to None.
        pump_info (Dict, optional): Details of a pump probe experiment eg. pump exposure time, pump delay, etc. Defaults to None.

    Raises:
        ValueError: When the chip information is missing.
    """
    logger.info("Write NeXus file for fixed target.")

    # Check that the chip dict has been passed, raise error is not
    if chip_info is None:
        logger.error("No chip_dict found.")
        raise ValueError(
            "No information about the FT chip has been passed. \
            Impossible to determine scan parameters. NeXus file won't be written."
        )

    chip = Chip(
        "fastchip",
        num_steps=[chip_info["X_NUM_STEPS"][1], chip_info["Y_NUM_STEPS"][1]],
        step_size=[chip_info["X_STEP_SIZE"][1], chip_info["Y_STEP_SIZE"][1]],
        num_blocks=[chip_info["X_NUM_BLOCKS"][1], chip_info["Y_NUM_BLOCKS"][1]],
        block_size=[chip_info["X_BLOCK_SIZE"][1], chip_info["Y_BLOCK_SIZE"][1]],
        start_pos=[
            chip_info["X_START"][1],
            chip_info["Y_START"][1],
            chip_info["Z_START"][1],
        ],
    )

    goniometer["increments"] = [0.0, 0.0, chip.step_size[1], chip.step_size[0]]
    # Read chip map
    blocks = read_chip_map(
        chipmap,
        chip.num_blocks[0],  # chip_info["X_NUM_BLOCKS"][1],
        chip.num_blocks[1],  # chip_info["Y_NUM_BLOCKS"][1],
    )

    # Calculate scan start/end positions on chip
    if list(blocks.values())[0] == "fullchip":
        logger.info("Full chip: all the blocks will be scanned.")
        start_pos, end_pos = compute_goniometer(chip, goniometer["axes"], full=True)
    else:
        logger.info(f"Scanning blocks: {list(blocks.keys())}.")
        start_pos, end_pos = compute_goniometer(chip, goniometer["axes"], blocks=blocks)

    # Iterate over blocks to calculate scan points
    OSC = {"omega": np.array([])}
    TRANSL = {"sam_y": np.array([]), "sam_x": np.array([])}
    for s, e in zip(start_pos.values(), end_pos.values()):
        goniometer["starts"] = s
        goniometer["ends"] = [
            end - inc for end, inc in zip(e, goniometer["increments"])
        ]  # Workaround for scanspec issue (we don't want to write the actual end of the chip)
        osc, transl = ScanReader(
            goniometer,
            n_images=(
                chip.num_steps[1],  # chip_info["Y_NUM_STEPS"][1],
                chip.num_steps[0],  # chip_info["X_NUM_STEPS"][1],
            ),
        )
        OSC["omega"] = np.append(OSC["omega"], osc["omega"])
        TRANSL["sam_y"] = np.append(TRANSL["sam_y"], np.round(transl["sam_y"], 3))
        TRANSL["sam_x"] = np.append(TRANSL["sam_x"], np.round(transl["sam_x"], 3))

    # Log data
    logger.info("Goniometer information")
    for j in range(len(goniometer["axes"])):
        logger.info(
            f"Goniometer axis: {goniometer['axes'][j]} => {goniometer['types'][j]} on {goniometer['depends'][j]}"
        )
    logger.info(f"Oscillation axis: {list(OSC.keys())[0]}.")
    logger.info(f"Grid scan axes: {list(TRANSL.keys())}.")

    if int(chip_info["N_EXPOSURES"][1]) == 1:
        # Check that things make sense
        if num_imgs != len(OSC["omega"]):
            logger.warning(
                f"The total number of scan points is {len(OSC['omega'])}, which does not match the total nu mber of images passed as input {num_imgs}."
            )
            logger.warning(
                "Reset SSX.num_imgs to number of scan points for vds creation"
            )
            tot_imgs = len(OSC["omega"])
        else:
            tot_imgs = num_imgs

        # Write NeXus and VDS
        try:
            with h5py.File(master_file, "x") as nxsfile:
                write_NXentry(nxsfile)

                call_writers(
                    nxsfile,
                    filename,
                    coordinate_frame,
                    (detector["mode"], tot_imgs),
                    goniometer,
                    detector,
                    module,
                    source,
                    beam,
                    attenuator,
                    OSC,
                    transl_scan=TRANSL,
                    metafile=metafile,
                    link_list=dset_links,
                )

                # Write pump-probe information if requested
                if pump_info:
                    logger.info("Write pump information to file.")
                    if pump_info["pump_exposure_time"] is None:
                        logger.warning(
                            "Pump exposure time has not been recorded and won't be written to file."
                        )
                    if pump_info["pump_delay"] is None:
                        logger.warning(
                            "Pump delay has not been recorded and won't be written to file."
                        )
                    # Add pump-repeat to info dictionary
                    pump_info["pump_repeat"] = chip_info["PUMP_REPEAT"][1]
                    loc = "/entry/source/notes"
                    write_NXnote(nxsfile, loc, pump_info)

                # Write VDS
                image_vds_writer(nxsfile, (int(num_imgs), *detector["image_size"]))

                if timestamps:
                    write_NXdatetime(nxsfile, timestamps)

                logger.info(f"The file {master_file} was written correctly.")
        except Exception as err:
            logger.exception(err)
            logger.info(
                f"An error occurred and {master_file} couldn't be written correctly."
            )

    else:
        N = int(chip_info["N_EXPOSURES"][1])
        logger.info(f"Each position has been collected {N} times.")
        pump_repeat = int(chip_info["PUMP_REPEAT"][1])
        logger.info(f"Pump repeat setting: {pump_repeat}")

        # Repeat each position N times
        OSC = {k: [val for val in v for _ in range(N)] for k, v in OSC.items()}
        TRANSL = {k: [val for val in v for _ in range(N)] for k, v in TRANSL.items()}

        # Check that things make sense
        if num_imgs != len(OSC["omega"]):
            logger.warning(
                f"The total number of scan points is {len(OSC['omega'])}, which does not match the total nu mber of images passed as input {num_imgs}."
            )
            logger.warning(
                "Reset SSX.num_imgs to number of scan points for vds creation"
            )
            tot_imgs = len(OSC["omega"])
        else:
            tot_imgs = num_imgs

        # Write NeXus file (for now no VDS)
        try:
            with h5py.File(master_file, "w") as nxsfile:
                write_NXentry(nxsfile)

                call_writers(
                    nxsfile,
                    filename,
                    coordinate_frame,
                    (detector["mode"], tot_imgs),
                    goniometer,
                    detector,
                    module,
                    source,
                    beam,
                    attenuator,
                    OSC,
                    transl_scan=TRANSL,
                    metafile=metafile,
                    link_list=dset_links,
                )

                # Write pump-probe information if requested
                if pump_info:
                    logger.info("Write pump information to file.")
                    if pump_info["pump_exposure_time"] is None:
                        logger.warning(
                            "Pump exposure time has not been recorded and won't be written to file."
                        )
                    if pump_info["pump_delay"] is None:
                        logger.warning(
                            "Pump delay has not been recorded and won't be written to file."
                        )
                    # Add pump-repeat to info dictionary
                    pump_info["pump_repeat"] = chip_info["PUMP_REPEAT"][1]
                    loc = "/entry/source/notes"
                    write_NXnote(nxsfile, loc, pump_info)

                # Write VDS
                # TODO discuss how VDS should be saved. All in one probably not ideal for this application.
                image_vds_writer(nxsfile, (int(num_imgs), *detector["image_size"]))
                # for offset in range(0, tot_imgs, n_windows_in_block*N)
                # image_vds_writer(nxsfile, (int(num_imgs), *detector["image_size"]), offset)

                if timestamps:
                    write_NXdatetime(nxsfile, timestamps)
            logger.info(f"The file {master_file} was written correctly.")
        except Exception as err:
            logger.exception(err)
            logger.info(
                f"An error occurred and {master_file} couldn't be written correctly."
            )


def grid_scan_3D(
    master_file: Path,
    filename: List[Path],
    num_imgs: int,
    chip_info: Dict,
    chipmap: Path | str,
    metafile: Path = None,
    timestamps: Tuple[str] = None,
    pump_info: Dict = None,
):
    """
    Write the NeXus file for 3D grid scans, pump probe and not.

    Args:
        master_file (Path): Path to the NeXus file to be written.
        filename (List[Path]):  List of paths to file.
        num_imgs (int): Total number of images passed as a beamline parameter.
        chip_info (Dict): Basic information about the chip in use and collection dynamics.
        chipmap (Path | str): Path to the chipmap file corresponding to the current collection.
        metafile (Path, optional): Path to the _meta.h5 file. Defaults to None.
        timestamps (Tuple[str], optional): Start and end time of data collection, if known. See docs for accepted formats. Defaults to None.
        pump_info (Dict, optional): Details of a pump probe experiment eg. pump exposure time, pump delay, etc. Defaults to None.

    Raises:
        ValueError: When the chip information is missing.
    """
    logger.info("Write NeXus file for 3D gid scan.")
    # The question here is ... what about rotation?

    logger.info("Write NeXus file for fixed target.")

    # Check that the chip dict has been passed, raise error is not
    if chip_info is None:
        logger.error("No chip_dict found.")
        raise ValueError(
            "No information about the FT chip has been passed. \
            Impossible to determine scan parameters. NeXus file won't be written."
        )

    chip = Chip(
        "fastchip",
        num_steps=[chip_info["X_NUM_STEPS"][1], chip_info["Y_NUM_STEPS"][1]],
        step_size=[chip_info["X_STEP_SIZE"][1], chip_info["Y_STEP_SIZE"][1]],
        num_blocks=[chip_info["X_NUM_BLOCKS"][1], chip_info["Y_NUM_BLOCKS"][1]],
        block_size=[chip_info["X_BLOCK_SIZE"][1], chip_info["Y_BLOCK_SIZE"][1]],
        start_pos=[
            chip_info["X_START"][1],
            chip_info["Y_START"][1],
            chip_info["Z_START"][1],
        ],
    )
    # Read chip map
    blocks = read_chip_map(
        chipmap,
        chip.num_blocks[0],  # chip_info["X_NUM_BLOCKS"][1],
        chip.num_blocks[1],  # chip_info["Y_NUM_BLOCKS"][1],
    )
    print(blocks)


def write_nxs(**ssx_params):
    """
    Gather all parameters from the beamline and call appropriate writer function for serial crystallography.
    """
    # Get info from the beamline
    SSX = ssx_collect(
        visitpath=Path(ssx_params["visitpath"]).expanduser().resolve(),
        filename=ssx_params["filename"],  # Template: test_##
        exp_type=ssx_params["exp_type"],
        num_imgs=float(ssx_params["num_imgs"]),
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
        flux=ssx_params["flux"],
        pump_status=ssx_params["pump_status"],
        pump_exp=ssx_params["pump_exp"],
        pump_delay=ssx_params["pump_delay"],
        chip_info=None
        if ssx_params["exp_type"] == "extruder"
        else ssx_params[
            "chip_info"
        ],  # ssx_params["chip_info"] if ssx_params["chip_info"] else None,
        chipmap=None
        if ssx_params["exp_type"] == "extruder"
        else Path(ssx_params["chipmap"]).expanduser().resolve(),
    )

    logfile = SSX.visitpath / "I24_nxs_writer.log"
    # Configure logging
    log.config(logfile.as_posix())

    # TODO check that detector distance is in mm.
    # Add to dictionaries
    detector["starts"] = [SSX.detector_distance]
    detector["exposure_time"] = SSX.exposure_time
    detector["beam_center"] = SSX.beam_center

    attenuator["transmission"] = SSX.transmission

    beam["wavelength"] = SSX.wavelength
    beam["flux"] = SSX.flux

    logger.info(f"Current collection directory: {SSX.visitpath}")
    # Find metafile in directory and get info from it
    try:
        metafile = [
            f for f in SSX.visitpath.iterdir() if SSX.filename + "_meta" in f.as_posix()
        ][0]
        logger.info(f"Found {metafile} in directory.")
    except IndexError:
        logger.warning(
            "No _meta.h5 file found in directory. External links in the NeXus file will be broken."
        )
        logger.error(
            "Missing metadata, unable to write NeXus file. Please use command line tool."
        )
        # TODO add instructions for using command line tool

    module["fast_axis"] = detector.pop("fast_axis")
    module["slow_axis"] = detector.pop("slow_axis")
    # Set value for module_offset calculation.
    module["module_offset"] = "1"

    # Find datafiles
    filename_template = (
        metafile.parent / metafile.name.replace("meta", f"{6*'[0-9]'}")
    ).as_posix()
    # if meta else (SSX.visitpath / SSX.filename).as_posix() + f"_{6*'[0-9]'}.h5"
    filename = [
        Path(f).expanduser().resolve() for f in sorted(glob.glob(filename_template))
    ]

    # Add some information to logger
    logger.info("Creating a NeXus file for %s ..." % metafile.name)
    # Get NeXus filename
    master_file = get_nexus_filename(filename[0])
    logger.info("NeXus file will be saved as %s" % master_file)

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

    logger.info(f"Recorded beam center is: {SSX.beam_center}.")

    # Get timestamps in the correct format
    timestamps = (
        get_iso_timestamp(SSX.start_time),
        get_iso_timestamp(SSX.stop_time),
    )
    logger.info(f"Timestamps recorded: {timestamps}")

    if SSX.pump_status == "true":
        logger.info("Pump status is True.")
        pump_info = {}
        pump_info["pump_exposure_time"] = SSX.pump_exp if SSX.pump_exp else None
        logger.info(f"Recorded pump exposure time: {SSX.pump_exp}")
        pump_info["pump_delay"] = SSX.pump_delay if SSX.pump_delay else None
        logger.info(f"Recorded pump delay time: {SSX.pump_delay}")
    else:
        pump_info = None

    # Call correct function for the current experiment
    if SSX.exp_type == "extruder":
        extruder(
            master_file, filename, int(SSX.num_imgs), metafile, timestamps, pump_info
        )
    elif SSX.exp_type == "fixed_target":
        fixed_target(
            master_file,
            filename,
            int(SSX.num_imgs),
            SSX.chip_info,
            SSX.chipmap,
            metafile,
            timestamps,
            pump_info,
        )
    elif SSX.exp_type == "3Dgridscan":
        grid_scan_3D(
            master_file,
            filename,
            int(SSX.num_imgs),
            SSX.chip_info,
            SSX.chipmap,
            metafile,
            timestamps,
            pump_info,
        )

    logger.info("*EOF*\n")


# # Example usage
# if __name__ == "__main__":
#     import sys
#     from datetime import datetime

#     write_nxs(
#         visitpath=sys.argv[1],
#         filename=sys.argv[2],
#         exp_type="extruder",
#         num_imgs=2450,
#         beam_center=[1590.7, 1643.7],
#         det_dist=0.5,
#         # start_time=None,
#         # stop_time=None,
#         start_time=datetime.now(),
#         stop_time=datetime.now(),
#         exp_time=0.002,
#         transmission=1.0,
#         wavelength=0.649,
#         flux=None,
#         pump_status="true",  # this is a string on the beamline
#         pump_exp=None,
#         pump_delay=None,
#         chip_info=None,
#         chipmap=None,
#     )
