"""
Create a NeXus file for serial crystallography datasets collected on Eiger detector either on I19-2 or I24 beamlines.
"""
from __future__ import annotations

import logging
from collections import namedtuple
from pathlib import Path

import h5py

from .. import log
from ..nxs_utils import Attenuator, Beam, Detector, EigerDetector, Goniometer, Source
from ..nxs_write.NXmxWriter import NXmxFileWriter
from ..tools.Metafile import DectrisMetafile
from ..tools.MetaReader import define_vds_data_type, update_axes_from_meta
from ..utils import find_in_dict, get_iso_timestamp
from .beamline_utils import PumpProbe, collection_summary_log

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
    if not find_in_dict("start_time", ssx_params):
        ssx_params["start_time"] = None
    if not find_in_dict("stop_time", ssx_params):
        ssx_params["stop_time"] = None

    SSX = ssx_collect(
        num_imgs=int(num_imgs),
        exposure_time=ssx_params["exp_time"]
        if find_in_dict("exp_time", ssx_params)
        else None,
        detector_distance=ssx_params["det_dist"]
        if find_in_dict("det_dist", ssx_params)
        else None,
        beam_center=ssx_params["beam_center"]
        if find_in_dict("beam_center", ssx_params)
        else (0, 0),
        transmission=ssx_params["transmission"]
        if find_in_dict("transmission", ssx_params)
        else None,
        wavelength=ssx_params["wavelength"]
        if find_in_dict("wavelength", ssx_params)
        else None,
        flux=ssx_params["flux"] if find_in_dict("flux", ssx_params) else None,
        start_time=ssx_params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if ssx_params["start_time"]
        else None,
        stop_time=ssx_params["stop_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if ssx_params["stop_time"]
        else None,
        chip_info=ssx_params["chip_info"]
        if find_in_dict("chip_info", ssx_params)
        else None,
        chipmap=ssx_params["chipmap"] if find_in_dict("chipmap", ssx_params) else None,
    )

    if expt_type.lower() not in ["extruder", "fixed-target", "3Dgridscan"]:
        raise ValueError("Unknown experiment type.")

    visitpath = Path(visitpath).expanduser().resolve()

    # Configure logging
    logfile = visitpath / f"{beamline}_EigerSSX_nxs_writer.log"
    log.config(logfile.as_posix())

    logger.info(f"Current collection directory: {visitpath.as_posix()}")
    # Get NeXus filename
    master_file = visitpath / f"{filename}.nxs"
    logger.info("NeXus file will be saved as %s" % master_file.as_posix())

    # Get parameters depending on beamline
    logger.info(f"DLS Beamline: {beamline.upper()}.")
    if "I19" in beamline.upper():
        source = Source("I19-2")
        osc_axis = ssx_params["osc_axis"] if "osc_axis" in ssx_params.keys() else "phi"
        from .I19_2_params import I19_2Eiger as axes_params

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
        from .I24_params import I24Eiger as axes_params

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
        pump_probe.pump_status = pump_status
        pump_probe.pump_exposure = (
            ssx_params["pump_exp"] if find_in_dict("pump_exp", ssx_params) else None
        )
        pump_probe.pump_delay = (
            ssx_params["pump_exp"] if find_in_dict("pump_exp", ssx_params) else None
        )

        logger.info(f"Recorded pump exposure time: {pump_probe.pump_exposure}")
        logger.info(f"Recorded pump delay time: {pump_probe.pump_delay}")
        if expt_type == "fixed-target":
            pump_probe.pump_repeat = int(SSX.chip_info["PUMP_REPEAT"][1])

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

    # Sanity check on det_z vs SSX.det_dist
    logger.debug("Sanity check on detector distance.")
    det_z_idx = [n for n, ax in enumerate(det_axes) if ax.name == "det_z"][0]
    if SSX.detector_distance and SSX.detector_distance != det_axes[det_z_idx].start_pos:
        logger.debug(
            "Detector distance value in meta file did not match with the one passed by the user.\n"
            f"Passed value: {SSX.detector_distance}; Value stored in meta file: {det_axes[det_z_idx].start_pos}.\n"
            "Value will be overwritten with the passed one."
        )
        det_axes[det_z_idx].start_pos = SSX.detector_distance

    # Define detector
    detector = Detector(
        eiger_params,
        det_axes,
        SSX.beam_center,
        SSX.exposure_time,
        [axes_params.fast_axis, axes_params.slow_axis],
    )

    tot_num_imgs = SSX.num_imgs

    # Run experiment type
    if expt_type == "extruder":
        from .SSX_expt import run_extruder

        gonio_axes, SCAN, pump_info = run_extruder(
            gonio_axes,
            tot_num_imgs,
            pump_probe,
            osc_axis,
        )
    elif expt_type == "fixed-target":
        from .SSX_expt import run_fixed_target

        # Define chipmap if needed
        chipmapfile = (
            "fullchip"
            if SSX.chipmap is None
            else Path(SSX.chipmap).expanduser().resolve()
        )

        SCAN, pump_info = run_fixed_target(
            gonio_axes,
            SSX.chip_info,
            chipmapfile,
            pump_probe,
            ["sam_y", "sam_x"],
        )

        # Sanity check that things make sense
        if SSX.num_imgs != len(SCAN["sam_x"]):
            logger.warning(
                f"The total number of scan points is {len(SCAN['sam_x'])}, which does not match the total number of images passed as input {SSX.num_imgs}."
            )
            logger.warning(
                "Reset SSX.num_imgs to number of scan points for vds creation."
            )
            tot_num_imgs = len(SCAN["sam_x"])
    else:
        print("3D")
        SCAN = {}  # tboth here here
        pump_info = pump_probe.to_dict()

    # Define goniometer only once the full scan has been calculated.
    goniometer = Goniometer(gonio_axes, SCAN)

    # Log a bunch of stuff
    collection_summary_log(
        logger,
        goniometer,
        detector,
        attenuator,
        beam,
        source,
        timestamps,
    )

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
            NXmx_Writer.add_NXnote(
                notes=pump_info,
                loc="/entry/source/notes",
            )
        NXmx_Writer.update_timestamps(timestamps[1], "end_time")
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
