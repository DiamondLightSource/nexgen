"""
Create a NeXus file for serial crystallography datasets collected on Eiger detector either on I19-2 or I24 beamlines.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal, get_args

import numpy as np
from numpy.typing import DTypeLike

from .. import log
from ..nxs_utils import Attenuator, Beam, Detector, EigerDetector, Goniometer, Source
from ..nxs_write.nxmx_writer import NXmxFileWriter
from ..utils import find_in_dict, get_iso_timestamp
from .beamline_utils import (
    BeamlineAxes,
    GeneralParams,
    PumpProbe,
    collection_summary_log,
)

# Define logger
logger = logging.getLogger("nexgen.SSX_Eiger")


EnabledBeamlines = Literal["i24", "i19-2"]
ExperimentTypes = Literal["extruder", "fixed-target"]  # TODO add "3Dgridscan"


class InvalidBeamlineError(Exception):
    def __init__(self, errmsg):
        logger.error(errmsg)


class UnknownExperimentTypeError(Exception):
    def __init__(self, errmsg):
        logger.error(errmsg)


class SerialParams(GeneralParams):
    """Collection parameters for a serial crystallography experiment.

    Args:
        GeneralParams (Basemodel): General collection parameters common to \
            multiple beamlines/experiments, such as exposure time, wavelength, ...
        num_imgs (int): Total number of frames in a collection.
        detector_distance (float): Distance between sample and deterctor, in mm.
        experiment_type (str): Type of collection.
    """

    num_imgs: int
    detector_distance: float
    experiment_type: str


def _define_vds_dtype_from_bit_depth(bit_depth: int) -> DTypeLike:
    """Define dtype of VDS based on the passed bit depth."""
    if bit_depth == 32:
        return np.uint32
    elif bit_depth == 8:
        return np.uint8
    else:
        return np.uint16


def _get_beamline_specific_params(beamline: str) -> tuple[BeamlineAxes, EigerDetector]:
    """Get beamline specific axes and eiger description.

    Args:
        beamline (str): Beamline name. Allowed values: i24, i19-2.

    Returns:
        tuple[BeamlineAxes, EigerDetector]: beamline axes description, eiger parameters.
    """
    match beamline.lower():
        case "i24":
            from .I24_params import I24Eiger as axes_params

            eiger_params = EigerDetector(
                "Eiger2 X 9M",
                (3262, 3108),
                "CdTe",
                50649,
                -1,
            )
        case "i19-2":
            from .I19_2_params import I19_2Eiger as axes_params

            eiger_params = EigerDetector(
                "Eiger2 X 4M",
                (2162, 2068),
                "CdTe",
                50649,
                -1,
            )
    return axes_params, eiger_params


def ssx_eiger_writer(
    visitpath: Path | str,
    filename: str,
    beamline: EnabledBeamlines,
    num_imgs: int,
    expt_type: ExperimentTypes = "fixed-target",
    pump_status: bool = False,
    **ssx_params,
):
    """Gather all collection parameters and write the NeXus file for SSX using Eiger detector.

    Args:
        visitpath (Path | str): Collection directory.
        filename (str): Filename root.
        beamline (str): Beamline on which the experiment is being run. Allowed values: i24, i19-2.
        num_imgs (int): Total number of images collected.
        expt_type (str, optional): Experiment type, accepted values: extruder,
            fixed-target, (coming soon: 3Dgridscan). Defaults to "fixed-target".
        pump_status (bool, optional): True for pump-probe experiment. Defaults to False.

    Keyword Args:
        bit_depth (int): bit_depth_image value, from which the vds_dtype is determined. \
            Will default to 32 if not passed.
        exp_time (float): Exposure time, in s.
        det_dist (float): Distance between sample and detector, in mm.
        beam_center (List[float, float]): Beam center position, in pixels.
        transmission (float): Attenuator transmission, in %.
        wavelength (float): Wavelength of incident beam, in A.
        flux (float): Total flux.
        start_time (datetime): Experiment start time.
        stop_time (datetime): Experiment end time.
        chip_info (Dict): For a grid scan, dictionary containing basic chip information.
            At least it should contain: x/y_start, x/y number of blocks and block size, \
            x/y number of steps and number of exposures.
        chipmap (list[int]): List of scanned blocks for the current collection. If not \
            passed or None for a fixed target experiment, it indicates that the fullchip is \
            being scanned.
        pump_exp (float): Pump exposure time, in s.
        pump_delay (float): Pump delay time, in s.
        osc_axis (str): Oscillation axis. Always omega on I24. If not passed it will \
            default to phi for I19-2.
        outdir (str): Directory where to save the file. Only specify if different \
            from meta_file directory.

    Raises:
        InvalidBeamlineError: If an invalid beamline name is passed.
        UnknownExperimentTypeError: If an invalid experiment type is passed.
    """
    # Beamline check
    if beamline.lower() not in get_args(EnabledBeamlines):
        raise InvalidBeamlineError(
            "Unknown beamline for SSX collections with Eiger detector."
            "Beamlines currently enabled for the writer: I24 (Eiger 9M), I19-2 (Eiger 4M)."
        )
    # Collect some of the params
    SSX = SerialParams(
        num_imgs=int(num_imgs),
        exposure_time=(
            ssx_params["exp_time"] if find_in_dict("exp_time", ssx_params) else 0.0
        ),
        detector_distance=(
            ssx_params["det_dist"] if find_in_dict("det_dist", ssx_params) else 0.0
        ),
        experiment_type=expt_type,
        beam_center=(
            ssx_params["beam_center"]
            if find_in_dict("beam_center", ssx_params)
            else (0, 0)
        ),
        wavelength=(
            ssx_params["wavelength"] if find_in_dict("wavelength", ssx_params) else None
        ),
        transmission=(
            ssx_params["transmission"]
            if find_in_dict("transmission", ssx_params)
            else None
        ),
        flux=ssx_params["flux"] if find_in_dict("flux", ssx_params) else None,
    )

    chip_info = (
        ssx_params["chip_info"] if find_in_dict("chip_info", ssx_params) else None
    )
    chipmap = ssx_params["chipmap"] if find_in_dict("chipmap", ssx_params) else None
    if isinstance(chipmap, list) and len(chipmap) == 0:
        chipmap = None

    if SSX.experiment_type.lower() not in get_args(ExperimentTypes):
        raise UnknownExperimentTypeError(
            f"Unknown experiment type, please pass one of {get_args(ExperimentTypes)}"
        )

    visitpath = Path(visitpath).expanduser().resolve()

    if find_in_dict("outdir", ssx_params) and ssx_params["outdir"]:
        wdir = Path(ssx_params["outdir"]).expanduser().resolve()
    else:
        wdir = visitpath

    # Configure logging
    logfile = wdir / f"{beamline}_EigerSSX_nxs_writer.log"
    log.config(logfile.as_posix())

    logger.info(f"Current collection directory: {visitpath.as_posix()}")
    if wdir != visitpath:
        logger.warning(f"Nexus file will be saved in a different directory: {wdir}")
    # Get NeXus filename
    master_file = wdir / f"{filename}.nxs"
    logger.info("NeXus file will be saved as %s" % master_file.as_posix())

    # Get parameters depending on beamline
    logger.info(f"DLS Beamline: {beamline.upper()}.")
    # Define source
    source = Source(beamline.upper())
    # Axes, eiger params
    axes_params, eiger_params = _get_beamline_specific_params(beamline)
    # Oscillation axis defaults to omega unless it's I19-2
    if beamline.lower() == "i19-2":
        osc_axis = ssx_params["osc_axis"] if "osc_axis" in ssx_params.keys() else "phi"
    else:
        osc_axis = "omega"

    # Define what to do based on experiment type
    logger.info(f"Running {SSX.experiment_type} collection.")

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
        if SSX.experiment_type == "fixed-target":
            pump_probe.pump_repeat = int(chip_info["PUMP_REPEAT"][1])

    # Get timestamps in the correct format
    _start_time = (
        ssx_params["start_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if find_in_dict("start_time", ssx_params) and ssx_params["start_time"]
        else None
    )
    _stop_time = (
        ssx_params["stop_time"].strftime("%Y-%m-%dT%H:%M:%S")
        if find_in_dict("stop_time", ssx_params) and ssx_params["stop_time"]
        else None
    )
    timestamps = (
        get_iso_timestamp(_start_time),
        get_iso_timestamp(_stop_time),
    )

    # Define meta file name and check if it has already appeared in the directory
    metafile = visitpath / f"{filename}_meta.h5"
    print(metafile)
    _check = [f for f in visitpath.iterdir() if f.name == metafile.name]
    if len(_check) == 0:
        logger.warning(
            """Meta file has not yet appeared in the visit directory.
            If still missing at the end of the collection, something may be wrong.
            Without a meta file, the links in the nexus file will be broken.
            """
        )
    else:
        logger.debug(f"Found {metafile} in directory.")

    # Define Attenuator
    attenuator = Attenuator(SSX.transmission)
    # Define Beam
    wl = SSX.wavelength
    if not wl:
        logger.warning("No value passed for wavelength, will be set to 0.0.")
        wl = 0.0
    beam = Beam(wl, SSX.flux)

    # Define vds_dtype from bit_depth
    if not find_in_dict("bit_depth", ssx_params):
        logger.warning("Bit depth not in parameters, will be assumed to be 32.")
        bit_depth = 32
    else:
        bit_depth = ssx_params["bit_depth"]
    vds_dtype = _define_vds_dtype_from_bit_depth(bit_depth)
    logger.debug(f"VDS dtype will be {vds_dtype}")

    # Define Goniometer axes
    gonio_axes = axes_params.gonio
    # Define Detector
    det_axes = axes_params.det_axes
    # Set det_z to detector_distance passed in mm
    det_z_idx = [n for n, ax in enumerate(det_axes) if ax.name == "det_z"][0]
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
    match SSX.experiment_type:
        case "extruder":
            from .SSX_expt import run_extruder

            gonio_axes, SCAN, pump_info = run_extruder(
                gonio_axes,
                tot_num_imgs,
                pump_probe,
                osc_axis,
            )
        case "fixed-target":
            from .SSX_expt import run_fixed_target

            SCAN, pump_info = run_fixed_target(
                gonio_axes,
                chip_info,
                pump_probe,
                chipmap,
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
        # TODO case "3D"

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
        image_filename = metafile.as_posix().replace("_meta.h5", "")
        NXmx_Writer.write(image_filename=image_filename, start_time=timestamps[0])
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
