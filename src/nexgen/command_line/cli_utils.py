"""
Writer for NeXus format files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from freephil.common import scope_extract as ScopeExtract

from ..nxs_utils import (
    Attenuator,
    Axis,
    Beam,
    Detector,
    DetectorType,
    EigerDetector,
    Facility,
    Goniometer,
    Source,
    TransformationType,
    TristanDetector,
)
from ..nxs_utils.detector import EIGER_CONST, UnknownDetectorTypeError
from ..nxs_write.nxmx_writer import EventNXmxFileWriter, NXmxFileWriter
from ..utils import coerce_to_path, coord2mcstas, imgcif2mcstas

logger = logging.getLogger("nexgen.cli_utils")


def add_tristan_spec(detector: ScopeExtract, tristanSpec: ScopeExtract):
    """
    Add metadata specific to LATRD Tristan to detector scope.

    Args:
        detector (scope_extract):      Scope defining the detector
        tristanSpec (scope_extract):   Scope defining Tristan specific input
    """
    for k, v in tristanSpec.__dict__.items():
        if "__phil" in k:
            continue
        detector.__inject__(k, v)


def phil2dict(D: Dict):
    l: List = [k for k in D.keys() if "__phil_" in k]
    for i in l:
        D.__delitem__(i)
    return D


def split_arrays(axes_names: List, array: List) -> Dict[str, Tuple]:
    """Split a list of values into arrays.

    This function splits up the list of values passed as input (eg. phil parameters, dictionary) \
    for vector, offset for all existing axes.

    Args:
        axes_names (List): Axes names.
        array (List): Array of values to be split up. It must be

    Raises:
        ValueError: When each axes doesn't have a corresponding array of size 3.

    Returns:
        array_dict (Dict[str, Tuple]): Dictionary of arrays corresponding to each axis. Keys are axes names.
    """
    array_dict = {}
    if len(axes_names) == len(array):
        array_dict = {ax: tuple(v) for ax, v in zip(axes_names, array)}
        return array_dict
    elif len(array) == 3 * len(axes_names):
        for j in range(len(axes_names)):
            a = array[3 * j : 3 * j + 3]
            array_dict[axes_names[j]] = tuple(a)
        return array_dict
    else:
        error_msg = (
            f"Number of axes {len(axes_names)} doesn't match the lenght of the array list {len(array)}."
            "Please check again and make sure that all axes have a matching array of size 3."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)


def reframe_arrays(
    goniometer: Dict[str, Any],
    detector: Dict[str, Any],
    module: Dict[str, Any],
    coordinate_frame: str = "mcstas",
    new_coord_system: Dict[str, Any] = None,
):
    """
    Split a list of offset/vector values into arrays. If the coordinate frame is not mcstas, \
    convert the arrays using the base vectors of the new coordinate system.

    Args:
        goniometer (Dict[str, Any]): Goniometer geometry description.
        detector (Dict[str, Any]): Detector specific parameters and its axes.
        module (Dict[str, Any]): Geometry and description of detector module.
        coordinate_frame (str, optional): Coordinate system being used. If "imgcif", there's no need to pass a \
            new coordinate system definition, as the conversion is already included in nexgen. Defaults to "mcstas".
        new_coord_system (Dict[str, Any], optional): Definition of the current coordinate system. \
            It should at least contain a string defining the convention, origin and axes information as a tuple of (depends_on, type, units, vector). \
            e.g. for X axis: {"x": (".", "translation", "mm", [1,0,0])}. \
            Defaults to None.

    Raises:
        ValueError: When the input coordinate system name and the coordinate system convention for the vectors doesn't match.
    """
    # If the arrays of vectors/offsets are not yet split, start by doing that
    goniometer["vectors"] = list(
        split_arrays(goniometer["axes"], goniometer["vectors"]).values()
    )
    goniometer["offsets"] = list(
        split_arrays(goniometer["axes"], goniometer["offsets"]).values()
    )

    detector["vectors"] = list(
        split_arrays(detector["axes"], detector["vectors"]).values()
    )

    if "offsets" in module.keys():
        module["offsets"] = list(
            split_arrays(["fast_axis", "slow_axis"], module["offsets"]).values()
        )

    # Now proceed with conversion if needed
    if coordinate_frame.lower() != "mcstas":
        if coordinate_frame.lower() == "imgcif":
            # Goniometer
            goniometer["vectors"] = [imgcif2mcstas(v) for v in goniometer["vectors"]]
            goniometer["offsets"] = [imgcif2mcstas(v) for v in goniometer["offsets"]]

            # Detector
            detector["vectors"] = [imgcif2mcstas(v) for v in detector["vectors"]]

            # Module
            module["fast_axis"] = imgcif2mcstas(module["fast_axis"])
            module["slow_axis"] = imgcif2mcstas(module["slow_axis"])
            if "offsets" in module.keys():
                module["offsets"] = [imgcif2mcstas(off) for off in module["offsets"]]
        else:
            if coordinate_frame != new_coord_system["convention"]:
                error_msg = (
                    "The input coordinate frame value doesn't match the current cordinate system convention."
                    "Impossible to convert to mcstas."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            mat = np.array(
                [
                    new_coord_system["x"][-1],
                    new_coord_system["y"][-1],
                    new_coord_system["z"][-1],
                ]
            )

            # Goniometer
            goniometer["vectors"] = [
                coord2mcstas(v, mat) for v in goniometer["vectors"]
            ]
            goniometer["offsets"] = [
                coord2mcstas(v, mat) for v in goniometer["offsets"]
            ]

            # Detector
            detector["vectors"] = [coord2mcstas(v, mat) for v in detector["vectors"]]

            # Module
            module["fast_axis"] = coord2mcstas(module["fast_axis"], mat)
            module["slow_axis"] = coord2mcstas(module["slow_axis"], mat)
            if "offsets" in module.keys():
                module["offsets"] = [
                    coord2mcstas(off, mat) for off in module["offsets"]
                ]


def _update_detector_constants(det_params: DetectorType, params: Dict):
    for k in list(det_params.constants.keys()):
        if k in list(params.keys()):
            det_params[k] = params[k]


def set_detector_params(
    det_name: str, use_meta: bool = False, **params
) -> DetectorType:
    """Set up the detector parameters from parsed input

    Args:
        det_name (str): Detector name.
        use_meta (bool, optional): Whether a meta file is present. Mostly important for Eiger links.

    Keyword Args:
        Required parameters to set up detector.
        For Eiger: {"description", "image_size", "sensor_material", "overload", "underload"}
        For Tristan: {"description", "image_size"}
        Plus any additional arguments fo overwrite constants.

    Raises:
        ValueError: When missing required tristan kwargs.
        ValueError: When missing required eiger kwargs.
        UnknownDetectorTypeError: Id a detector drifferent from tristan or eiger has been requested.

    Returns:
        DetectorType: Parameters which define the detector in use.
    """
    if "tristan" in det_name.lower():
        required_params = {"description", "image_size"}
        if not required_params.issubset(params.keys()):
            logger.error("Missing detector parameters information for Tristan.")
            raise ValueError("Missing tristan information.")
        det_params = TristanDetector(params["description"], params["image_size"])
        if len(params.keys()) > 2:
            _update_detector_constants(det_params, params)
    elif "eiger" in det_name.lower():
        required_params = {
            "description",
            "image_size",
            "sensor_material",
            "overload",
            "underload",
        }
        if not required_params.issubset(params.keys()):
            logger.error("Missing detector parameters information for Eiger.")
            raise ValueError("Missing eiger information.")
        det_params = EigerDetector(
            params["description"],
            params["image_size"],
            params["sensor_material"],
            params["overload"],
            params["underload"],
        )
        if use_meta is False and len(params.keys()) > 5:
            _update_detector_constants(det_params, params)
        if use_meta is False and len(params.keys()) == 5:
            for k in list(det_params.constants.keys()):
                det_params.constants[k] = None
    else:
        error_msg = "This CLI functionality is currently only available for Eiger and Tristan detectors."
        logger.error(error_msg)
        raise UnknownDetectorTypeError(error_msg)
    return det_params


# Write NeXus base classes
def call_writers(
    nxsfile: Path | str,
    datafiles: List[Path | str],
    coordinate_frame: str,
    data_type: Tuple[str, int],
    goniometer: Dict[str, Any],
    detector: Dict[str, Any],
    module: Dict[str, Any],
    source: Dict[str, Any],
    beam: Dict[str, Any],
    attenuator: Dict[str, Any],
    metafile: bool = False,
    timestamps: Tuple[str, str] = None,
    notes: Dict[str, Any] = None,
):
    """
    Call the writers for the NeXus base classes.

    Args:
        nxsfile (Path | str): NeXus file to be written.
        datafiles (List[Path | str]): List of at least 1 Path object to a HDF5 data file.
        coordinate_frame (str): Coordinate system being used. Accepted frames are imgcif and mcstas.
        data_type (Tuple[str, int]): Images or event-mode data, and eventually how many are being written.
        goniometer (Dict[str, Any] Goniometer geometry description.
        detector (Dict[str, Any]): Detector specific parameters and its axes.
        module (Dict[str, Any]): Geometry and description of detector module.
        source (Dict[str, Any]): Facility information.
        beam (Dict[str, Any]): Beam properties.
        attenuator (Dict[str, Any]): Attenuator properties.
        metafile (bool, optional): Whether a metafile is present. Defaults to False.
        timestamps (Tuple[str], optional): Start and end collection timestamps in ISO format. Defaults to None.
        notes (Dict, optional): Any additional information to write as NXnote. Defaults to None.
    """
    logger.info("Calling the writer ...")
    nxsfile = coerce_to_path(nxsfile)

    # Split vectors and offsets in goniometer and detector for writing
    reframe_arrays(
        goniometer,
        detector,
        module,
        coordinate_frame,
    )

    # Check that filenames are paths
    datafiles = [coerce_to_path(f) for f in datafiles]

    # Set up Source, Beam, Attenuator
    attenuator_new = Attenuator(attenuator["transmission"])
    beam_new = Beam(beam["wavelength"], beam["flux"])
    facility = Facility(
        source["name"], source["short_name"], source["type"], source["facility_id"]
    )
    source_new = Source(source["beamline_name"], facility, source["probe"])

    # Other params that might have been passed
    if "eiger" in detector["description"].lower():
        contants = {
            k: detector[k]
            for k in list(EIGER_CONST.keys())
            if k in list(detector.keys())
        }
    else:
        contants = {}

    # Set up detector
    detector_params = set_detector_params(
        detector["description"],
        metafile,
        image_size=detector["image_size"],
        sensor_material=detector["sensor_material"],
        overload=detector["overload"],
        underload=["underload"],
        **contants,
    )
    det_axes = []
    for idx, ax in enumerate(detector["axes"]):
        transf = (
            TransformationType.TRANSLATION
            if "translation" == detector["types"][idx]
            else TransformationType.ROTATION
        )
        a = Axis(
            ax,
            detector["depends"][idx],
            transf,
            detector["vectors"][idx],
            start_pos=detector["starts"][idx],
        )
        det_axes.append(a)
    det = Detector(
        detector_params,
        det_axes,
        detector["beam_center"],
        detector["exposure_time"],
        [module["fast_axis"], module["slow_axis"]],
    )

    # Set up gonio
    gonio_axes = []
    for idx, ax in enumerate(goniometer["axes"]):
        transf = (
            TransformationType.TRANSLATION
            if "translation" == goniometer["types"][idx]
            else TransformationType.ROTATION
        )
        num = 0 if goniometer["increments"][idx] == 0 else data_type[1]
        a = Axis(
            ax,
            goniometer["depends"][idx],
            transf,
            goniometer["vectors"][idx],
            start_pos=goniometer["starts"][idx],
            increment=goniometer["increments"][idx],
            num_steps=num if data_type[0] == "images" else 0,
        )
        gonio_axes.append(a)

    # Scan can be identified by goniometer functionality
    gonio = Goniometer(gonio_axes)

    # Aaaand write
    if data_type[0] == "images":
        writer = NXmxFileWriter(
            nxsfile,
            gonio,
            det,
            source_new,
            beam_new,
            attenuator_new,
            data_type[1],
        )
        writer.write(image_datafiles=datafiles, start_time=timestamps[0])
        writer.write_vds()
    else:
        writer = EventNXmxFileWriter(
            nxsfile, gonio, det, source_new, beam_new, attenuator_new
        )
        writer.write(start_time=timestamps[0])

    if notes:
        writer.add_NXnote(notes, "/entry/notes")

    if timestamps[1]:
        writer.update_timestamps(timestamps[1])
