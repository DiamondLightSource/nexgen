"""
Command line tool to create a NeXus file for time-resolved collections on I19-2.
Available detectors: Tristan 10M, Eiger 2X 4M.
"""

import argparse
import logging
from collections import namedtuple
from datetime import datetime

from ..command_line import version_parser

logger = logging.getLogger("nexgen.I19-2_NeXus_cli")


def gda_writer():
    """
    Write a NeXus file starting from information passed by GDA.
    """
    logger.info("")

    from .I19_2_gda_nxs import write_nxs

    parser = argparse.ArgumentParser(
        description="Create a NeXus file for I19-2 interfacing with GDA.",
        parents=[version_parser],
    )
    parser.add_argument("meta_file", type=str, help="Path to _meta.h5 file.")
    parser.add_argument("xml_file", type=str, help="Path to GDA generated xml file.")
    parser.add_argument(
        "detector_name",
        type=str,
        choices=["eiger", "tristan"],
        help="Detector currently in use on beamline.",
    )
    parser.add_argument("exp_time", type=str, help="Exposure time, in s.")
    parser.add_argument("wavelength", type=str, help="Incident beam wavelength.")
    parser.add_argument(
        "beam_center_x", type=str, help="Beam center x position, in pixels."
    )
    parser.add_argument(
        "beam_center_y", type=str, help="Beam center y position, in pixels."
    )
    parser.add_argument(
        "--start", "--start-time", type=str, default=None, help="Collection start time."
    )
    parser.add_argument(
        "--stop", "--stop-time", type=str, default=None, help="Collection end time."
    )
    parser.add_argument(
        "--geom",
        "--geometry-json",
        type=str,
        default=None,
        help="Path to GDA generated geometry json file.",
    )
    parser.add_argument(
        "--det",
        "--detector-json",
        type=str,
        default=None,
        help="Path to GDA generated detector json file.",
    )
    args = parser.parse_args()

    write_nxs(
        meta_file=args.meta_file,
        xml_file=args.xml_file,
        detector_name=args.detector_name,  # e.g. "tristan", "eiger",
        exposure_time=float(args.exp_time),
        wavelength=float(args.wavelength),
        beam_center=[
            float(args.beam_center_x),
            float(args.beam_center_y),
        ],
        start_time=datetime.strptime(args.start, "%Y-%m-%dT%H:%M:%SZ")
        if args.start
        else None,
        stop_time=datetime.strptime(args.stop, "%Y-%m-%dT%H:%M:%SZ")
        if args.stop
        else None,  # datetime.now(),
        geometry_json=args.geom if args.geom else None,
        detector_json=args.det if args.det else None,
    )


def nexgen_writer():
    """
    Write a NXmx format NeXus file from the I19-2 beamline.
    """
    logger.info("")

    from . import detAx_parser, gonioAx_parser
    from .I19_2_nxs import nexus_writer

    parser = argparse.ArgumentParser(
        description="Create a NeXus file for I19-2 data.",
        parents=[version_parser, gonioAx_parser, detAx_parser],
    )
    parser.add_argument("meta_file", type=str, help="Path to _meta.h5 file.")
    parser.add_argument(
        "detector_name", type=str, help="Detector currently in use on beamline."
    )
    parser.add_argument("exp_time", type=float, help="Exposure time, in s.")
    parser.add_argument(
        "-tr",
        "--transmission",
        type=float,
        default=None,
        help="Attenuator transmission.",
    )
    parser.add_argument(
        "-wl",
        "--wavelength",
        type=float,
        default=None,
        help="Incident beam wavelength, in A.",
    )
    parser.add_argument(
        "-bc",
        "--beam-center",
        type=float,
        nargs="+",
        help="Beam center (x,y) positions.",
    )
    parser.add_argument(
        "--start", "--start-time", type=str, default=None, help="Collection start time."
    )
    parser.add_argument(
        "--stop", "--stop-time", type=str, default=None, help="Collection end time."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output directory for new NeXus file, if different from collection directory.",
    )
    args = parser.parse_args()

    if args.axes and not args.ax_start:
        raise IOError(
            "Please pass start and increment values for each of the goniometer axes indicated."
        )
    if args.det_axes and not args.det_start:
        raise IOError(
            "Please pass start and increment values for each of the detector axes indicated."
        )

    if args.axes and args.ax_start:
        if args.detector_name == "eiger":
            axes = namedtuple("axes", ("id", "start", "inc"))
            axes_list = []
            for ax, s, i in zip(args.axes, args.ax_start, args.ax_inc):
                axes_list.append(axes(ax, s, i))
        else:
            axes = namedtuple("axes", ("id", "start", "end"))
            axes_list = []
            for ax, s, e in zip(args.axes, args.ax_start, args.ax_end):
                axes_list.append(axes(ax, s, e))

    if args.det_axes and args.det_start:
        det_axes = namedtuple("det_axes", ("id", "start"))
        det_list = []
        for ax, s in zip(args.det_axes, args.det_start):
            det_list.append(det_axes(ax, s))

    # Check that an actual meta file has been passed and not a data file
    if "meta" not in args.meta_file:
        logger.error(
            f"Wrong input file passed: {args.meta_file}. Please pass the _meta.h5 file for this dataset."
        )
        raise IOError(
            "The input file passed is not a _meta.h5 file. Please pass the correct file."
        )

    nexus_writer(
        meta_file=args.meta_file,
        detector_name=args.detector_name,
        exposure_time=args.exp_time,
        transmission=args.transmission if args.transmission else None,
        wavelength=args.wavelength if args.wavelength else None,
        beam_center=args.beam_center if args.beam_center else None,
        start_time=datetime.strptime(args.start, "%Y-%m-%dT%H:%M:%SZ")
        if args.start
        else None,
        stop_time=datetime.strptime(args.stop, "%Y-%m-%dT%H:%M:%SZ")
        if args.stop
        else None,
        scan_axis=args.scan_axis if args.scan_axis else None,
        gonio_pos=axes_list if args.axes else None,
        det_pos=det_list if args.det_axes else None,
        outdir=args.output if args.output else None,
    )
