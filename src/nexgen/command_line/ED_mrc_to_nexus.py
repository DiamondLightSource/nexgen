"""
A script to convert a series of individual MRC images into a Nexus format.
"""

import logging
import os
from argparse import ArgumentParser
from dataclasses import asdict, dataclass
from logging import Logger
from pathlib import Path

import numpy as np

from nexgen.beamlines.ED_params import (
    ED_coord_system,
    EDCeta,
    EDSource,
)
from nexgen.nxs_utils import (
    Attenuator,
    Beam,
    CetaDetector,
    Detector,
    Goniometer,
)
from nexgen.nxs_utils.scan_utils import calculate_scan_points
from nexgen.nxs_write.ed_nxmx_writer import EDNXmxFileWriter
from nexgen.tools.mrc_tools import get_metadata, to_hdf5_data_file

logger = logging.getLogger("nexgen.ED_mrc_to_nexus")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()  # Logs to stdout
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


@dataclass
class Metadata:
    mrc_files: list[str | Path]
    detector_name: str = "unknown"
    facility_name: str = "unknown"
    facility_id: str = "unknown"
    facility_short_name: str = "unknown"
    facility_type: str = "Electron Source"
    detector_distance: float = None
    wavelength: float = None
    angle_start: float = None
    angle_increment: float = None
    exposure_time: float = None
    beam_center: tuple[float, float] | list[float] = None
    rotation_axis: tuple[float, float, float] = (0, -1, 0)
    fast_axis: tuple[float, float, float] = (-1, 0, 0)
    slow_axis: tuple[float, float, float] = (0, -1, 0)
    pixel_size: float = None
    sensor_material: str = "Si"
    sensor_thickness: float = 0.0
    detector_type: str = "CMOS"
    overload: float = None
    underload: float = None
    data_type: str = None
    original_data_type: str = None
    pixel_number_x: int = None
    pixel_number_y: int = None
    num_images: int = None
    source: str = "electron"


def check_metadata(
    metadata_template: Metadata,
    logger: Logger,
) -> None:
    """Check if some metadata variables are not set"""

    for key, value in asdict(metadata_template).items():
        if value is None:
            msg = f"Metadata {key} is not set."
            raise ValueError(msg)

    logger.info("Listing parameters to be written in the Nexus file: ")
    log_dict(logger, metadata_template)


def overwrite_from_tvips(
    metadata_template: Metadata, logger: Logger, mrc_metadata: dict
) -> None:
    """Set default parameters describing TVIPS detector"""

    m = metadata_template

    nx = mrc_metadata["nx"]
    ny = mrc_metadata["ny"]

    if (nx == 4096) and (ny == 4096):
        binning = 1
    elif (nx == 2048) and (ny == 2048):
        binning = 2
    elif (nx == 1024) and (ny == 1024):
        binning = 4
    elif (nx == 512) and (ny == 512):
        binning = 8
    else:
        msg = f"Non standard detector size ({nx}, {ny})."
        msg += "Expecting (4096/b, 4096/b) with binning b = 1, 2, 4, 8"
        raise ValueError(msg)

    m.detector_name = "TVIPS Detector"
    m.pixel_size = 0.015500 * binning
    m.overload = 8000 * binning**2
    m.underload = 0
    m.beamline = "TVIPS"
    m.rotation_axis = (1, 0, 0)
    logger.info("Setting default TVIPS parameters.")


def overwrite_from_cetad(
    metadata_template: Metadata, logger: Logger, mrc_metadata: dict
) -> dict:
    """Set default parameters describing CetaD detector"""

    m = metadata_template
    msg = "Nexus file does not save detector gain. Gain for Ceta-D is 26."
    logger.warning(msg)

    m.detector_name = "Thermo Fisher Ceta-D"
    nx = mrc_metadata["nx"]
    ny = mrc_metadata["ny"]

    m.pixel_num_x = nx
    m.pixel_num_y = ny

    if (nx == 2048) and (ny == 2048):
        binning = 2
    else:
        binning = 1

    m.pixel_size = 0.014 * binning
    m.overload = 8000 * binning**2
    m.underload = -1000
    m.facility = "Diamond Light Source"
    m.facility_short_name = ""
    m.facility_type = "Electron Source"
    m.facility_id = "DIAMOND"
    m.beamline = "Ceta-D-eBIC"
    m.data_type = "int32"

    logger.info("Setting default Ceta-D parameters.")


def overwrite_from_mrc(metadata_template, logger, mrc_metadata):
    """Overwrites the metadata template with metadata from the MRC file"""

    if len(mrc_metadata["data_shape"]) == 3:
        metadata_template.num_images = mrc_metadata["data_shape"][0]
    else:
        metadata_template.num_images = len(metadata_template.mrc_files)

    if "cameraLength" in mrc_metadata:
        metadata_template.detector_distance = mrc_metadata["cameraLength"]
        msg = "Setting detector distance from the MRC files: "
        msg += "%.1f" % mrc_metadata["cameraLength"]
        logger.info(msg)

    if "wavelength" in mrc_metadata:
        metadata_template.wavelength = mrc_metadata["wavelength"]
        msg = "Setting wavelength from the MRC files: "
        msg += f"{mrc_metadata['wavelength']}"
        logger.info(msg)

    if "alphaTilt" in mrc_metadata:
        metadata_template.angle_start = mrc_metadata["alphaTilt"]
        msg = "Setting starting angle (alphaTilt) from the MRC files: "
        msg += f"{mrc_metadata['alphaTilt']}"
        logger.info(msg)

    if "tiltPerImage" in mrc_metadata:
        metadata_template.angle_increment = mrc_metadata["tiltPerImage"]
        msg = "Setting rotation angle increment from the MRC files: "
        msg += "%f" % mrc_metadata["tiltPerImage"]
        logger.info(msg)

    if "integrationTime" in mrc_metadata:
        metadata_template.exposure_time = mrc_metadata["integrationTime"]
        msg = "Setting exposure time from the MRC files: "
        msg += "%f" % mrc_metadata["integrationTime"]
        logger.info(msg)

    if ("beamCentreXpx" in mrc_metadata) and ("beamCentreYpx" in mrc_metadata):
        bc = (mrc_metadata["beamCentreXpx"], mrc_metadata["beamCentreYpx"])
        metadata_template.beam_center = bc
        msg = "Setting beam center from the MRC files: (%.1f, %.1f)" % bc
        logger.info(msg)

    m = metadata_template
    m.data_type = "%s" % mrc_metadata["original_data_type"]
    m.original_data_type = "%s" % mrc_metadata["original_data_type"]
    msg = "Default data type in the MRC files: "
    msg += "%s" % mrc_metadata["original_data_type"]
    logger.info(msg)

    m.pixel_number_x = mrc_metadata["nx"]
    m.pixel_number_y = mrc_metadata["ny"]


def overwrite_from_command_line(
    template: Metadata, logger: Logger, cmd_args: dict, mrc_metadata: dict
) -> None:
    """Overwrite the metadata with the arguments from the command line"""

    if cmd_args.detector_name is not None:
        template.detector_name = cmd_args.detector_name
        msg = "Detector name overwritten from the command line: "
        msg += cmd_args.detector_name
        logger.info(msg)

    if cmd_args.facility_name is not None:
        template.facility_name = cmd_args.facility_name
        msg = "Facility overwritten from the command line: "
        msg += cmd_args.facility_name
        logger.info(msg)

    if cmd_args.facility_id is not None:
        template.facility_id = cmd_args.facility_id
        msg = "Facility ID overwritten from the command line: "
        msg += cmd_args.facility_id
        logger.info(msg)

    if cmd_args.facility_short_name is not None:
        template.facility_short_name = cmd_args.facility_short_name
        msg = "Facility short name overwritten from the command line: "
        msg += cmd_args.facility_short_name
        logger.info(msg)

    if cmd_args.detector_distance is not None:
        template.detector_distance = cmd_args.detector_distance
        msg = "Detector distance overwritten from the command line: "
        msg += "%f" % cmd_args.detector_distance
        logger.info(msg)

    if cmd_args.wavelength is not None:
        template.wavelength = cmd_args.wavelength
        msg = "Wavelength overwritten from the command line: "
        msg += "%f" % cmd_args.wavelength
        logger.info(msg)

    if cmd_args.angle_start is not None:
        template.angle_start = cmd_args.angle_start
        msg = "Starting angle overwritten from the command line: "
        msg += "%f" % cmd_args.angle_start
        logger.info(msg)

    if cmd_args.angle_increment is not None:
        template.angle_increment = cmd_args.angle_increment
        msg = "Angle increment overwritten from the command line: "
        msg += "%f" % cmd_args.angle_increment
        logger.info(msg)

    if cmd_args.exposure_time is not None:
        template.exposure_time = cmd_args.exposure_time
        msg = "Exposure time overwritten from the command line: "
        msg += "%f" % cmd_args.exposure_time
        logger.info(msg)

    if cmd_args.beam_center is not None:
        template.beam_center = cmd_args.beam_center
        x, y = cmd_args.beam_center
        msg = "Beam center overwritten from the command line: "
        msg += f"{x:.2f}, {y:.2f}"
        logger.info(msg)

    if cmd_args.rotation_axis is not None:
        template.rotation_axis = cmd_args.rotation_axis
        x, y, z = cmd_args.rotation_axis
        msg = "Rotation axis overwritten from the command line: "
        msg += "(%.1f, %.1f, %.1f)" % (x, y, z)
        logger.info(msg)

    if cmd_args.slow_axis is not None:
        template.slow_axis = cmd_args.slow_axis
        x, y, z = cmd_args.slow_axis
        msg = "Slow axis overwritten from the command line: "
        msg += "(%.1f, %.1f, %.1f)" % (x, y, z)
        logger.info(msg)

    if cmd_args.fast_axis is not None:
        template.fast_axis = cmd_args.fast_axis
        x, y, z = cmd_args.fast_axis
        msg = "Fast axis overwritten from the command line: "
        msg += "(%.1f, %.1f, %.1f)" % (x, y, z)
        logger.info(msg)

    if cmd_args.pixel_size is not None:
        template.pixel_size = cmd_args.pixel_size
        msg = "Pixel size overwritten from the command line: "
        msg += "%.10f" % cmd_args.pixel_size
        logger.info(msg)

    if cmd_args.sensor_material is not None:
        template.sensor_material = cmd_args.sensor_material
        msg = "Sensor material overwritten from the command line: "
        msg += "%s" % cmd_args.sensor_material
        logger.info(msg)

    if cmd_args.sensor_thickness is not None:
        template.sensor_thickness = cmd_args.sensor_thickness
        msg = "Sensor thickness overwritten from the command line: "
        msg += "%f" % cmd_args.sensor_thickness
        logger.info(msg)
    if abs(template.sensor_thickness - 0.0) < 1.0e-30:
        template.sensor_thickness = 1.0e-30
        msg = "Sensor thickness can not be zero. Setting it to 1.e-15."
        logger.info(msg)

    if cmd_args.detector_type is not None:
        template.detector_type = cmd_args.detector_type
        msg = "Detector type overwritten from the command line: "
        msg += "%s" % cmd_args.detector_type
        logger.info(msg)

    if cmd_args.data_type is not None:
        template.data_type = cmd_args.data_type
        msg = "Data type overwritten from the command line: "
        msg += "%s" % cmd_args.data_type
        logger.info(msg)

    if cmd_args.source is not None:
        template.source = cmd_args.source
        msg = "Source overwritten from the command line: "
        msg += "%s" % cmd_args.source
        logger.info(msg)

    if cmd_args.overload is not None:
        template.overload = cmd_args.overload
        msg = "Detector overload overwritten from the command line: "
        msg += "%d" % cmd_args.overload
        logger.info(msg)

    if cmd_args.underload is not None:
        template.underload = cmd_args.underload
        msg = "Detector underload overwritten from the command line: "
        msg += "%d" % cmd_args.underload
        logger.info(msg)


def log_dict(logger: Logger, dictionary: dict, skip: list = None) -> None:

    if skip is None:
        skip = [1]

    msg = ""
    for index, (name, value) in enumerate(asdict(dictionary).items()):
        if index in skip:
            buffer = ""
        else:
            buffer = 33 * " "

        if index != len(asdict(dictionary)) - 1:
            end_string = "\n"
        else:
            end_string = ""

        if value is not None and name != "mrc_files":
            msg += buffer + f"{name} = {value}" + end_string
    logger.info(msg)


def main():

    args = parse_input_arguments()
    metadata_template = Metadata(args.input_files)
    logger.info("Starting MRC to Nexus conversion.")

    for file in args.input_files:
        if not file.endswith(".mrc"):
            raise ValueError("Not an MRC file: %s" % file)

    mrc_files = args.input_files
    mrc_metadata = get_metadata(mrc_files[0])
    logger.info("Collecting MRC data into a HDF5 h5 file.")

    if args.detector == "cetad":
        logger.info("Detector set to cetad.")
        overwrite_from_cetad(metadata_template, logger, mrc_metadata)
    elif args.detector == "tvips":
        logger.info("Detector set to tvips.")
        overwrite_from_tvips(metadata_template, logger, mrc_metadata)

    overwrite_from_mrc(metadata_template, logger, mrc_metadata)
    overwrite_from_command_line(metadata_template, logger, args, mrc_metadata)
    check_metadata(metadata_template, logger)

    m = metadata_template

    gonio_axes = EDCeta.gonio
    gonio_axes[0].start_pos = m.angle_start
    gonio_axes[0].increment = m.angle_increment
    gonio_axes[0].num_steps = m.num_images
    EDCeta.gonio[0].vector = m.rotation_axis
    EDCeta.fast_axis = m.fast_axis
    EDCeta.slow_axis = m.slow_axis

    scan = calculate_scan_points(
        gonio_axes[0], rotation=True, tot_num_imgs=m.num_images
    )

    goniometer = Goniometer(gonio_axes, scan)

    hdf5_file = to_hdf5_data_file(mrc_files, logger, dtype=metadata_template.data_type)

    det_params = CetaDetector(m.detector_name, [m.pixel_number_x, m.pixel_number_y])

    ps_str = "%5.7fmm" % m.pixel_size
    det_params.pixel_size = [ps_str, ps_str]
    det_params.sensor_material = m.sensor_material
    det_params.sensor_thickness = m.sensor_thickness
    det_params.overload = m.overload
    det_params.underload = m.underload
    det_params.detector_type = m.detector_type

    extra_params = {}
    nx = m.pixel_number_x
    ny = m.pixel_number_y

    mask = np.zeros((nx, ny), dtype=np.int32)
    flatfield = np.ones((nx, ny), dtype=np.float32)
    extra_params["pixel_mask"] = mask
    extra_params["flatfield"] = flatfield
    extra_params["pixel_mask_applied"] = 1
    extra_params["flatfield_applied"] = 1
    det_params.constants.update(extra_params)

    det_axes = EDCeta.det_axes
    det_axes[0].start_pos = m.detector_distance

    EDSource.beamline = m.facility_name
    EDSource.facility_id = m.facility_id
    EDSource.facility_type = m.facility_type
    EDSource.probe = m.source
    EDSource.short_name = m.facility_short_name

    beam = Beam(m.wavelength)

    detector = Detector(
        det_params,
        det_axes,
        m.beam_center,
        m.exposure_time,
        [EDCeta.fast_axis, EDCeta.slow_axis],
    )

    path = os.getcwd()

    nexus_file = hdf5_file.replace("h5", "nxs")
    nexus_path = os.path.join(path, nexus_file)

    data_path = os.path.join(path, hdf5_file)
    data_path = Path(data_path)

    logger.info("Writing Nexus file.")

    attenuator = Attenuator(transmission=None)

    writer = EDNXmxFileWriter(
        nexus_path,
        goniometer,
        detector,
        EDSource,
        beam,
        attenuator,
        m.num_images,
        ED_coord_system,
    )

    writer.write([data_path], "/entry/data/data")
    writer.write_vds(vds_dtype=m.data_type, datafiles=[data_path])
    logger.info("MRC images converted to Nexus.")


def parse_input_arguments():

    msg = "Convert electron diffraction data from an MRC format "
    msg += "to a NeXus format"
    parser = ArgumentParser(description=msg, add_help=True)

    parser.add_argument(
        "--detector",
        type=str,
        default="cetad",
        choices=["cetad", "tvips", "unknown"],
        help="Detector type.",
    )

    parser.add_argument(
        "--detector-name",
        type=str,
        help="Detector name.",
    )

    parser.add_argument(
        "--facility-name",
        type=str,
        default=None,
        help="Name of the facility (e.g. Diamond Light Source).",
    )

    parser.add_argument(
        "--facility-short-name",
        type=str,
        default=None,
        help="Short name of the facility (e.g. DLS).",
    )

    parser.add_argument(
        "--facility-type",
        type=str,
        default=None,
        help="Facility type (e.g. Electron Source).",
    )

    msg = "Facility ID (e.g. DIAMOND). "
    msg += "Naming tries to follow the recommended convention for NXmx: "
    msg += "https://mmcif.wwpdb.org/dictionaries/"
    msg += "mmcif_pdbx_v50.dic/Items/_diffrn_source.type.html"
    parser.add_argument("--facility-id", type=str, default=None, help=msg)

    parser.add_argument(
        "--detector-distance",
        type=float,
        default=None,
        help="The sample-detector distance (in mm).",
    )

    parser.add_argument(
        "-wl",
        "--wavelength",
        type=float,
        default=None,
        help="Incident beam wavelength (in Angstroms).",
    )

    parser.add_argument(
        "--angle-start",
        type=float,
        default=None,
        help="Starting angle of a rotation scan (degrees).",
    )

    parser.add_argument(
        "--angle-increment",
        type=float,
        default=None,
        help="Angle increment of a rotation scan (degrees).",
    )

    parser.add_argument(
        "-e",
        "--exposure-time",
        type=float,
        help="Exposure time (in seconds).",
    )

    parser.add_argument(
        "-bc",
        "--beam-center",
        type=float,
        nargs=2,
        help="Beam center (x, y) or (fast, slow), in pixels.",
    )

    parser.add_argument(
        "--rotation-axis",
        type=float,
        nargs=3,
        help="Rotation axis (x, y, z).",
    )

    parser.add_argument(
        "--fast-axis",
        type=float,
        nargs=3,
        help="Detector fast axis (x, y, z).",
    )

    parser.add_argument(
        "--slow-axis",
        type=float,
        nargs=3,
        help="Detector slow axis (x, y, z).",
    )

    parser.add_argument(
        "--data-type",
        type=str,
        default=None,
        help="Data type for the HDF5 output (int32, int64, float64, ...).",
    )

    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Source type (e.g. electron, x-ray).",
    )

    parser.add_argument(
        "--pixel-size",
        type=float,
        default=None,
        help="Pixel size in mm.",
    )

    parser.add_argument(
        "--sensor-material",
        type=str,
        default=None,
        help="Sensor material (e.g. Si).",
    )

    parser.add_argument(
        "--sensor-thickness",
        type=float,
        default=None,
        help="Sensor thickness.",
    )

    parser.add_argument(
        "--detector-type",
        type=str,
        default=None,
        help="Detector type (e.g. CMOS).",
    )

    parser.add_argument(
        "--overload",
        type=float,
        default=None,
        help="Upper limit of the trusted range.",
    )

    parser.add_argument(
        "--underload",
        type=float,
        default=None,
        help="Lower limit of the trusted range.",
    )

    des = "List of input files. Can be a single MRC file containing all the "
    des += "images, or a list of files containing single images, "
    des += "usually obtained by global expansion (e.g. *mrc)"
    parser.add_argument("input_files", nargs="+", help=des)

    args = parser.parse_args()

    return args
