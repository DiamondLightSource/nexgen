"""
Command line tool to generate NXmx-like NeXus files for Electron Diffraction.
"""

from __future__ import annotations

import argparse
import glob
import logging
from pathlib import Path

from .. import log
from ..beamlines.ED_params import ED_coord_system
from ..beamlines.ED_singla_nxs import singla_nexus_writer
from ..nxs_utils import Axis, TransformationType
from . import config_parser, version_parser
from .cli_config import CliConfig

logger = logging.getLogger("nexgen.EDNeXusGeneratorCLI")

usage = "%(prog)s <sub-command> [options]"
parser = argparse.ArgumentParser(
    usage=usage, description=__doc__, parents=[version_parser]
)


def write_from_SINGLA(args):

    singla_nexus_writer(
        args.master_file,
        args.det_distance,
        args.exp_time,
        n_imgs=args.n_imgs if args.n_imgs else None,
        scan_axis=[args.axis_name, args.axis_start, args.axis_inc],
        beam_center=args.beam_center if args.beam_center else None,
        wavelength=args.wavelength if args.wavelength else None,
        outdir=args.output,
        start_time=args.start if args.start else None,
    )


def write_from_SINGLA_from_config(args):
    if not args.config:
        raise IOError(
            "Please pass a YAML/JSON file with the configuration to use this functionality."
        )
    params = CliConfig.from_file(args.config)

    datafiles = [
        Path(f).expanduser().resolve() for f in sorted(glob.glob(args.datafiles))
    ]

    logger.warning("Have you checked the coordinate system convention?\n")

    # If anything has been passed regarding the new coordinate system convention
    # overwrite the existing dictionary
    if params.coord_system.convention:
        logger.info(
            f"New coordinate system convention: {params.coord_system.convention}."
        )
        ED_coord_system["convention"] = params.coord_system.convention
    else:
        logger.info("The following convention will be applied:\n" f"{ED_coord_system}")

    if params.coord_system.origin:
        logger.info(
            f"New value for coordinate system found: {params.coord_system.origin}."
        )
        ED_coord_system["origin"] = tuple(params.coord_system.origin)

    if params.coord_system.vectors:
        vectors = {}
        for v, ax in zip(params.coord_system.vectors, ["x", "y", "z"]):
            vectors[ax] = v

        logger.info(
            f"New vectors defined for {params.coord_system.convention} coordinate system."
        )
        ED_coord_system["x"] = Axis(
            "x", ".", TransformationType.TRANSLATION, vectors["x"]
        )
        ED_coord_system["y"] = Axis(
            "y", "x", TransformationType.TRANSLATION, vectors["y"]
        )
        ED_coord_system["z"] = Axis(
            "z", "y", TransformationType.TRANSLATION, vectors["z"]
        )

    # Source info from cli
    new_source = {
        "name": params.source.facility.name,
        "facility_id": params.source.facility.id,
        "beamline": params.source.beamline,
        "probe": params.source.probe,
    }

    # Find scan axis in parsed values
    scan_idx = [
        n
        for n, ax in enumerate(params.gonio.axes)
        if ax.transformation_type == "rotation"
    ][0]
    scan_info = [
        params.gonio.axes[scan_idx].name,
        params.gonio.axes[scan_idx].start_pos,
        params.gonio.axes[scan_idx].increment,
    ]

    singla_nexus_writer(
        args.master,
        params.det.axes[0].start_pos,
        params.det.exposure_time,
        ED_coord_system,
        datafiles,
        args.convert,
        n_imgs=args.n_imgs,
        scan_axis=scan_info,
        beam_center=params.det.beam_center,
        wavelength=params.instrument.beam.wavelength,
        outdir=args.output,
        new_source_info=new_source,
    )


# Define some useful parsers
output_parser = argparse.ArgumentParser(add_help=False)
output_parser.add_argument(
    "-o",
    "--output",
    type=str,
    help="Output directory if different from location of data files.",
)

# Define subparsers
subparsers = parser.add_subparsers(
    help="Define what to do with input file depending on their origin.",
    required=True,
    dest="sub-command",
)
singla1_parser = subparsers.add_parser(
    "singla",
    description=("Trigger NeXus file writing for Singla data."),
    parents=[output_parser],
)
singla1_parser.add_argument(
    "master_file",
    type=str,
    help="HDF5 master file written by Singla detector.",
)
singla1_parser.add_argument(
    "det_distance",
    type=float,
    help="The sample-detector distance.",
)
singla1_parser.add_argument(
    "--axis-name",
    type=str,
    default="alpha",
    help="Rotation axis name",
)
singla1_parser.add_argument(
    "--axis-start",
    type=float,
    default=0.0,
    help="Rotation axis start position.",
)
singla1_parser.add_argument(
    "--axis-inc",
    type=float,
    default=0.0,
    help="Rotation axis increment.",
)
singla1_parser.add_argument(
    "-e",
    "--exp-time",
    type=float,
    required=True,
    help="Exposure time, in s.",
)
singla1_parser.add_argument(
    "-wl",
    "--wavelength",
    type=float,
    default=None,
    help="Incident beam wavelength, in A.",
)
singla1_parser.add_argument(
    "-bc",
    "--beam-center",
    type=float,
    nargs=2,
    help="Beam center (x,y) positions.",
)
singla1_parser.add_argument(
    "-n",
    "--n-imgs",
    type=int,
    help="Total number of images",
)
singla1_parser.add_argument(
    "--start", "--start-time", type=str, default=None, help="Collection start time."
)
singla1_parser.set_defaults(func=write_from_SINGLA)

singla2_parser = subparsers.add_parser(
    "singla-phil",
    description=("Trigger NeXus file writing for Singla data, using a phil parser."),
    parents=[config_parser, output_parser],
)
singla2_parser.add_argument(
    "master",
    type=str,
    required=True,
    help="HDF5 master file written by Singla detector.",
)
singla2_parser.add_argument(
    "datafiles",
    type=str,
    nargs="+",
    required=True,
    help="List of input data files with full path",
)
singla2_parser.add_argument(
    "-n",
    "-n-imgs",
    type=int,
    help="Total number of images collected.",
)
singla2_parser.add_argument(
    "--convert",
    action="store_true",
    help="If passed, convert vectors to mcstas if required.",
)
singla2_parser.set_defaults(func=write_from_SINGLA_from_config)


def main():
    log.config()
    args = parser.parse_args()
    args.func(args)
