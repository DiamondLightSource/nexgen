"""
A script to convert a series of individual MRC images into a Nexus format.
"""

import logging
import os
from argparse import ArgumentParser
from pathlib import Path

import numpy as np

from nexgen.beamlines.ED_params import ED_coord_system, EDCeta, EDSource
from nexgen.nxs_utils import Attenuator, Beam, CetaDetector, Detector, Goniometer
from nexgen.nxs_utils.scan_utils import calculate_scan_points
from nexgen.nxs_write.ed_nxmx_writer import EDNXmxFileWriter
from nexgen.tools.mrc_tools import collect_data, get_metadata

logger = logging.getLogger("nexgen.ED_mrc_to_nexus")


def main():

    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        "--det_distance",
        type=float,
        default=None,
        help="The sample-detector distance.",
    )
    parser.add_argument(
        "-wl",
        "--wavelength",
        type=float,
        default=None,
        help="Incident beam wavelength, in A.",
    )
    parser.add_argument(
        "--axis-start",
        type=float,
        default=None,
        help="Rotation axis start position.",
    )
    parser.add_argument(
        "--axis-inc",
        type=float,
        default=None,
        help="Rotation axis increment.",
    )
    parser.add_argument(
        "-e",
        "--exp-time",
        type=float,
        help="Exposure time, in s.",
    )
    parser.add_argument(
        "-bc",
        "--beam-center",
        type=float,
        nargs=2,
        help="Beam center (x,y) positions.",
    )
    parser.add_argument("input_files", nargs="+", help="List of input files")

    args = parser.parse_args()

    logger.info("Starting MRC to Nexus conversion")

    for file in args.input_files:
        if not file.endswith(".mrc"):
            raise ValueError("Not an MRC file: %s" % file)

    mrc_files = args.input_files
    full_mrc_path = os.path.abspath(mrc_files[0])
    logger.info("Collecting MRC data into a h5 file")
    tot_imgs, out_file, angles = collect_data(mrc_files)

    mdict = get_metadata(mrc_files[0])

    attenuator = Attenuator(transmission=None)

    if args.det_distance is not None:
        det_distance = args.det_distance
    elif "cameraLength" in mdict:
        det_distance = mdict["cameraLength"]
        msg = "Reading detector distance from "
        msg += "the MRC files: %.1f" % det_distance
        logger.info(msg)
    else:
        msg = "No detector distance in the MRC metadata. "
        msg += "You can set it with -det_distance option."
        raise ValueError(msg)

    if args.wavelength is not None:
        beam = Beam(args.wavelength)
    elif "wavelength" in mdict:
        beam = Beam(mdict["wavelength"])
        msg = "Reading wavelength from the MRC files: %f" % mdict["wavelength"]
        logger.info(msg)
    else:
        msg = "No wavelength in the MRC metadata. "
        msg += "You can set it with --wavelength option."
        raise ValueError(msg)

    if args.axis_start is not None:
        start_angle = args.axis_start
    elif angles[0] is not None:
        start_angle = angles[0]
        msg = "Reading starting angle from the MRC files: %.2f" % start_angle
        logger.info(msg)
    else:
        msg = "No starting angle in the MRC metadata. "
        msg += "You can set it with --axis_start option."
        raise ValueError(msg)

    if args.axis_inc is not None:
        increment = args.axis_inc
    elif "tiltPerImage" in mdict:
        increment = mdict["tiltPerImage"]
        msg = "Reading angle increment from the MRC files: %f" % increment
        logger.info(msg)
    else:
        msg = "No angle increment in the MRC metadata. "
        msg += "You can set it with --axis_inc option."
        raise ValueError(msg)

    if args.exp_time is not None:
        exposure_time = args.exp_time
    elif "integrationTime" in mdict:
        exposure_time = mdict["integrationTime"]
        msg = "Reading exposure time from the MRC files: %f" % exposure_time
        logger.info(msg)
    else:
        msg = "No exposure time in the MRC metadata. "
        msg += "You can set it with --exp_time option."
        raise ValueError(msg)

    if args.beam_center is not None:
        if len(args.beam_center) == 2:
            x, y = args.beam_center
            beam_center = (x, y)
        else:
            msg = "Beam center requires two arguments"
            raise ValueError(msg)
    elif ("beamCentreXpx" in mdict) and ("beamCentreYpx" in mdict):
        beam_center = (mdict["beamCentreXpx"], mdict["beamCentreYpx"])
        msg = "Reading beam center from the MRC files: (%.1f, %.1f)" % beam_center
        logger.info(msg)
    else:
        msg = "No beam center in the MRC metadata. "
        msg += "You can set it with --beam_center option."
        raise ValueError(msg)

    gonio_axes = EDCeta.gonio
    gonio_axes[0].start_pos = start_angle
    gonio_axes[0].increment = increment
    gonio_axes[0].num_steps = tot_imgs

    scan = calculate_scan_points(gonio_axes[0], rotation=True, tot_num_imgs=tot_imgs)
    goniometer = Goniometer(gonio_axes, scan)

    nx = mdict["nx"]
    ny = mdict["ny"]

    if (nx == 2048) and (ny == 2048):
        binning = 2
    else:
        binning = 1

    det_params = CetaDetector("Thermo Fisher Ceta-D", [nx, ny])

    pixel_size = 0.014 * binning
    ps_str = "%5.3fmm" % pixel_size
    det_params.pixel_size = [ps_str, ps_str]
    det_params.overload = 8000 * binning**2

    extra_params = {}
    mask = np.zeros((nx, ny), dtype=np.int32)
    flatfield = np.ones((nx, ny), dtype=np.float32)
    extra_params["pixel_mask"] = mask
    extra_params["flatfield"] = flatfield
    extra_params["pixel_mask_applied"] = 1
    extra_params["flatfield_applied"] = 1
    det_params.constants.update(extra_params)

    det_axes = EDCeta.det_axes

    det_axes[0].start_pos = det_distance

    detector = Detector(
        det_params,
        det_axes,
        beam_center,
        exposure_time,
        [EDCeta.fast_axis, EDCeta.slow_axis],
    )

    source = EDSource
    source.beamline = "Ceta"

    script_dir = os.path.dirname(full_mrc_path)
    file_name = out_file.replace("h5", "nxs")
    full_path = os.path.join(script_dir, file_name)
    data_path = os.path.join(script_dir, out_file)
    data_path = Path(data_path)

    msg = "Writing the Nexus file %s" % full_path
    logger.info(msg)
    writer = EDNXmxFileWriter(
        full_path,
        goniometer,
        detector,
        source,
        beam,
        attenuator,
        tot_imgs,
        ED_coord_system,
    )

    datafiles = [data_path]
    writer.write(datafiles, "/entry/data/data")
    writer.write_vds(vds_dtype=np.int32, datafiles=datafiles)
    logger.info("MRC images converted to Nexus.")
