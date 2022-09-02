"""
Command line tool to create a NeXus file for time-resolved collections on I19-2.
Available detectors: Tristan 10M, Eiger 2X 4M.
"""

import argparse
import logging
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
        "detector_name", type=str, help="Detector currently in use on beamline."
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
        ],  # [1590.7, 1643.7],
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
    """_summary_"""
    logger.info()

    from . import detAx_parser, gonioAx_parser

    parser = argparse.ArgumentParser(
        description="Create a NeXus file for I19-2 data.",
        parents=[version_parser, gonioAx_parser, detAx_parser],
    )
    parser.add_argument("meta_file", type=str, help="Path to _meta.h5 file.")
    parser.add_argument(
        "detector_name", type=str, help="Detector currently in use on beamline."
    )
    parser.add_argument("exp_time", type=float, help="Exposure time, in s.")
    parser.add_argument("transmission", type=float, help="Attenuator transmission.")
    parser.add_argument(
        "--wavelength", type=float, default=None, help="Incident beam wavelength, in A."
    )
    parser.add_argument(
        "--beam-center", type=float, nargs="+", help="Beam center (x,y) positions."
    )
    parser.add_argument(
        "--start", "--start-time", type=str, default=None, help="Collection start time."
    )
    parser.add_argument(
        "--stop", "--stop-time", type=str, default=None, help="Collection end time."
    )
    args = parser.parse_args()
    print(args)


# TODO change in setup.cfg:
# I19_nexus = nexgen.beamlines.I19_2_cli:gda_writer
# I19_new_nexus = nexgen.beamlines.I19_2_cli:nexgen_writer
