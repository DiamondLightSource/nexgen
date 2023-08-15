"""
Writer for NeXus format files.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import h5py
import numpy as np
from freephil.common import scope_extract as ScopeExtract  # Define scope extract type
from numpy.typing import ArrayLike
from scanspec.core import Path as ScanPath
from scanspec.specs import Line

from ..nxs_write.NXclassWriters import (
    write_NXdata,
    write_NXdatetime,
    write_NXdetector,
    write_NXdetector_module,
    write_NXentry,
    write_NXinstrument,
    write_NXnote,
    write_NXsample,
    write_NXsource,
)
from ..nxs_write.write_utils import find_number_of_images
from ..tools.DataWriter import generate_event_files, generate_image_files
from ..tools.MetaReader import overwrite_beam, overwrite_detector
from ..tools.VDS_tools import image_vds_writer, vds_file_writer
from ..utils import coord2mcstas, get_filename_template, imgcif2mcstas, units_of_time


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
        raise ValueError(
            f"Number of axes {len(axes_names)} doesn't match the lenght of the array list {len(array)}."
            "Please check again and make sure that all axes have a matching array of size 3."
        )


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
                raise ValueError(
                    "The input coordinate frame value doesn't match the current cordinate system convention."
                    "Impossible to convert to mcstas."
                )
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


def find_osc_axis(
    axes_names: List,
    axes_starts: List,
    axes_ends: List,
    axes_types: List,
    default: str = "omega",
) -> str:
    """
    Identify the rotation scan_axis.

    This function identifies the scan axis from the list passed as argument.
    The scan axis is the one where start and end value are not the same.
    If there is only one rotation axis, that is the one returned.
    In the case scan axis cannot be identified, a default value is arbitrarily assigned.

    Args:
        axes_names (List): List of names associated to goniometer axes.
        axes_starts (List): List of start values.
        axes_ends (List): List of end values.
        axes_types (List): List of axes types, useful to identify only the rotation axes.
        default (str, optional): String to deafult to in case scan axis is not found. Defaults to "omega".

    Raises:
        ValueError: If no axes have been passed.
        ValueError: If more than one rotation axis seems to move.

    Returns:
        scan_axis (str): String identifying the rotation scan axis.
    """
    # This assumes that at least one rotation axis is always passed.
    # Assuming all list are of the same length ...
    if len(axes_names) == 0:
        raise ValueError(
            "Impossible to determine translation scan. No axes passed to find_osc_axis function. Please make sure at least one value is passed."
        )
    # assert len(axes_names) > 0, "Please pass at least one axis."
    # Look only for rotation axes
    rot_idx = [i for i in range(len(axes_types)) if axes_types[i] == "rotation"]
    axes_names = [axes_names[j] for j in rot_idx]
    axes_starts = [axes_starts[j] for j in rot_idx]
    axes_ends = [axes_ends[j] for j in rot_idx]

    if len(axes_names) == 1:
        scan_axis = axes_names[0]
    else:
        idx = [(i != j) for i, j in zip(axes_starts, axes_ends)]
        if idx.count(True) == 0:
            # just in case ...
            scan_axis = default
        elif idx.count(True) == 1:
            scan_axis = axes_names[idx.index(True)]
        else:
            raise ValueError("Unable to correctly identify the rotation scan axis.")
    return scan_axis


def find_grid_scan_axes(
    axes_names: List,
    axes_starts: List,
    axes_ends: List,
    axes_types: List,
) -> List[str]:
    """
    Identify the scan axes for a linear/grid scan.

    Args:
        axes_names (List): List of names associated to goniometer axes.
        axes_starts (List): List of start values.
        axes_ends (List): List of end values.
        axes_types (List): List of axes types, useful to identify only the translation axes.

    Raises:
        ValueError: If no axes have been passed.

    Returns:
        scan_axis (List[str]): List of strings identifying the linear/grid scan axes. If no axes are identified, it will return an empty list.
    """
    if len(axes_names) == 0:
        raise ValueError(
            "Impossible to determine translation scan. No axes passed to find_grid_scan_axes function. Please make sure at least one value is passed."
        )

    # Look only at translation axes
    grid_idx = [i for i in range(len(axes_names)) if axes_types[i] == "translation"]
    axes_names = [axes_names[j] for j in grid_idx]
    axes_starts = [axes_starts[j] for j in grid_idx]
    axes_ends = [axes_ends[j] for j in grid_idx]

    scan_axis = []
    for n, ax in enumerate(axes_names):
        if axes_starts[n] != axes_ends[n]:
            scan_axis.append(ax)
    return scan_axis


def calculate_scan_range(
    axes_names: List,
    axes_starts: List,
    axes_ends: List,
    axes_increments: List = None,
    n_images: Tuple | int = None,
    snaked: bool = True,
    rotation: bool = False,
) -> Dict[str, ArrayLike]:
    """
    Calculate the scan range for a linear/grid scan or a rotation scan from the number of images to be written.
    If the number of images is not provided, it can be calculated from the increment value of the axis (these values are mutually exclusive).
    When dealing with a rotation axis, if there are multiple images but no rotation scan, return axis_start repeated n_images times.

    Args:
        axes_names (List): List of names for the axes involved in the scan.
        axes_starts (List): List of axis positions at the beginning of the scan.
        axes_ends (List): List of axis positions at the end of the scan.
        axes_increments (List, optional): List of ranges through which the axes move each frame. Mostly used for rotation scans. Defaults to None.
        n_images (Tuple | int, optional): Number of images to be written. If writing a 2D scan, it should be a (nx, ny) tuple, \
                                        where tot_n_img=nx*ny, any int value is at this time ignored. Defaults to None.
        snaked (bool): If True, scanspec will "draw" a snaked grid. Defaults to True.
        rotation (bool): Tell the function to calculate a rotation scan. Defaults to False.

    Raises:
        TypeError: If the input axes are not lists.
        ValueError: When an empty axes names list has been passed.
        ValueError: When both axes_increments and n_images have been passed. The two values are mutually exclusive.
        ValueError: When neither axes_increments not n_images have been passed.
        ValueError: For a grid scan, if axes_increments is None, n_images must be a tuple of len=2 to be sure to accurately calculate the scan points.

    Returns:
        Dict[str, ArrayLike]: A dictionary of ("axis_name": axis_range) key-value pairs.
    """
    if type(axes_names) is not list or type(axes_starts) is not list or type(axes_ends) is not list:
        raise TypeError("Input values for axes must be passed as lists.")

    if len(axes_names) == 0:
        raise ValueError("No axes have been passed, impossible to determine scan.")

    if n_images and axes_increments:
        raise ValueError(
            "The axes_increments and n_images arguments are mutually exclusive. Please pass just one of those."
            "For a 2D scan it is recommended that n_images is passed."
        )
    elif not n_images and not axes_increments:
        raise ValueError(
            "Impossible to calculate scan points, please pass either the axes increment values or the number of scan points (n_images) per axis."
            "For a 2D scan it is recommended that n_images is passed."
        )

    if len(axes_names) == 1 and rotation is True:
        if not n_images:
            n_images = round(abs(axes_starts[0] - axes_ends[0]) / axes_increments[0])

        if axes_starts[0] != axes_ends[0] and axes_increments:
            if axes_starts[0] > axes_ends[0]:
                # Account for reverse rotation.
                axes_ends[0] = axes_ends[0] + axes_increments[0]
            else:
                axes_ends[0] = axes_ends[0] - axes_increments[0]
        elif axes_starts[0] != axes_ends[0] and not axes_increments:
            inc = (axes_ends[0] - axes_starts[0]) / n_images
            axes_ends[0] = axes_ends[0] - inc

        spec = Line(axes_names[0], axes_starts[0], axes_ends[0], n_images)
        scan_path = ScanPath(spec.calculate())

    elif len(axes_names) == 1 and rotation is False:
        if not n_images:
            # FIXME This calculation still gives the wrong increment between scan points.
            n_images = (
                round(abs(axes_starts[0] - axes_ends[0]) / axes_increments[0]) + 1
            )
        elif type(n_images) is tuple and len(n_images) == 1:
            # This is mostly a double paranoid check
            n_images = n_images[0]

        spec = Line(axes_names[0], axes_starts[0], axes_ends[0], n_images)
        scan_path = ScanPath(spec.calculate())

    else:
        if not n_images:
            # FIXME This calculation still gives the wrong increment between scan points.
            n_images0 = (
                round(abs(axes_starts[0] - axes_ends[0]) / axes_increments[0]) + 1
            )
            n_images1 = (
                round(abs(axes_starts[1] - axes_ends[1]) / axes_increments[1]) + 1
            )
        elif len(n_images) == 1:
            raise ValueError(
                "Impossible to correctly calculate scan points from just the total number of images."
                "Please either pass a tuple with the number of scan point per axis or the axes increments."
            )
        else:
            n_images0 = n_images[0]
            n_images1 = n_images[1]

        if snaked is True:
            spec = Line(axes_names[0], axes_starts[0], axes_ends[0], n_images0) * ~Line(
                axes_names[1], axes_starts[1], axes_ends[1], n_images1
            )
        else:
            spec = Line(axes_names[0], axes_starts[0], axes_ends[0], n_images0) * Line(
                axes_names[1], axes_starts[1], axes_ends[1], n_images1
            )
        scan_path = ScanPath(spec.calculate())

    return scan_path.consume().midpoints


# Define the scan.
def ScanReader(
    goniometer: Dict,
    data_type: str = "images",
    n_images: int | Tuple = None,
    snaked: bool = True,
    osc_axis: str = None,
) -> Tuple[Dict, Dict]:
    """
    Read the information passed from the goniometer and return a definition of the scan.

    Args:
        goniometer (Dict): Goniometer geometry definition.
        data_type (str, optional): Type of data being written, can be images of events. Defaults to "images".
        n_images (int | Tuple, optional): Total number of images to write. If passed, \
                                    the number of images will override the axis_increment value of the rotation scan. \
                                    Defaults to None.
        snaked (bool, optional): 2D scan parameter. If True, defines a snaked grid scan. Defaults to True.

    Raises:
        ValueError: If the total number of images passed doesn't match the number of scan points when dealing with a 2D/3D scan.

    Returns:
        Tuple[Dict, Dict]: Two separate dictionaries. The first defines the rotation scan, the second the linear/grid scan. \
                            When dealing with a set of stills or a simple rotation scan, the second value will return None.
    """
    logger = logging.getLogger("nexgen.ScanReader")
    logger.setLevel(logging.DEBUG)
    # First find which axes deifne a rotation/translation scan
    if osc_axis is None:
        osc_axis = find_osc_axis(
            goniometer["axes"],
            goniometer["starts"],
            goniometer["ends"],
            goniometer["types"],
        )
    osc_idx = goniometer["axes"].index(osc_axis)
    transl_axes = find_grid_scan_axes(
        goniometer["axes"],
        goniometer["starts"],
        goniometer["ends"],
        goniometer["types"],
    )

    # If there's a linear/grid scan, get dictionary
    if len(transl_axes) > 0:
        transl_idx = [goniometer["axes"].index(j) for j in transl_axes]
        transl_start = [goniometer["starts"][i] for i in transl_idx]
        transl_end = [goniometer["ends"][i] for i in transl_idx]
        transl_increment = [goniometer["increments"][i] for i in transl_idx]
        if n_images and type(n_images) is int:
            TRANSL = calculate_scan_range(
                transl_axes,
                transl_start,
                transl_end,
                transl_increment,
                # (n_images,),
                snaked=snaked,
            )
        elif n_images and type(n_images) is tuple:
            TRANSL = calculate_scan_range(
                transl_axes, transl_start, transl_end, n_images=n_images, snaked=snaked
            )
        else:
            TRANSL = calculate_scan_range(
                transl_axes, transl_start, transl_end, transl_increment, snaked=snaked
            )
        logger.debug(f"{len(transl_axes)} scan axis/axes found (translation).")
    else:
        TRANSL = None

    # Once that's defined, go through the various cases
    # Return either 2 dictionaries or (Dict, None)
    if data_type == "events" and len(transl_axes) == 0:
        OSC = {osc_axis: (goniometer["starts"][osc_idx], goniometer["ends"][osc_idx])}
    elif data_type == "events" and len(transl_axes) > 0:
        OSC = {osc_axis: (goniometer["starts"][osc_idx], goniometer["ends"][osc_idx])}
        # Overwrite TRANSL
        # FIXME This is actually not needed.
        for k, s, e in zip(transl_axes, transl_start, transl_end):
            TRANSL[k] = (s, e)
    else:
        if n_images is None and len(transl_axes) == 0:
            OSC = calculate_scan_range(
                [osc_axis],
                [goniometer["starts"][osc_idx]],
                [goniometer["ends"][osc_idx]],
                axes_increments=[goniometer["increments"][osc_idx]],
                rotation=True,
            )
        elif n_images is None and len(transl_axes) > 0:
            ax = transl_axes[0]
            n_images = len(TRANSL[ax])
            OSC = calculate_scan_range(
                [osc_axis],
                [goniometer["starts"][osc_idx]],
                [goniometer["ends"][osc_idx]],
                n_images=n_images,
                rotation=True,
            )
        elif n_images is not None and len(transl_axes) > 0:
            ax = transl_axes[0]
            n_images = np.prod(n_images) if type(n_images) is tuple else n_images
            if n_images != len(TRANSL[ax]):
                raise ValueError(
                    "The value passed as the total number of images doesn't match the number of scan points, please check the input."
                )
            #
            OSC = calculate_scan_range(
                [osc_axis],
                [goniometer["starts"][osc_idx]],
                [goniometer["ends"][osc_idx]],
                n_images=n_images,
                rotation=True,
            )
        else:
            n_images = np.prod(n_images) if type(n_images) is tuple else n_images
            OSC = calculate_scan_range(
                [osc_axis],
                [goniometer["starts"][osc_idx]],
                [goniometer["ends"][osc_idx]],
                n_images=n_images,
                rotation=True,
            )

    logger.debug(f"{osc_axis} set as rotation axis.")
    return OSC, TRANSL


# Write NeXus base classes
def call_writers(
    nxsfile: h5py.File,
    datafiles: List[Path | str],
    coordinate_frame: str,
    data_type: Tuple[str, int],
    goniometer: Dict[str, Any],
    detector: Dict[str, Any],
    module: Dict[str, Any],
    source: Dict[str, Any],
    beam: Dict[str, Any],
    attenuator: Dict[str, Any],
    osc_scan: Dict[str, ArrayLike],
    transl_scan: Dict[str, ArrayLike] = None,
    metafile: Path | str = None,
    link_list: List = None,
    sample_depends_on: str = None,
):
    """
    Call the writers for the NeXus base classes.

    Args:
        nxsfile (h5py.File): NeXus file to be written.
        datafiles (List[Path |str]): List of at least 1 Path object to a HDF5 data file.
        coordinate_frame (str): Coordinate system being used. Accepted frames are imgcif and mcstas.
        data_type (Tuple[str, int]): Images or event-mode data, and eventually how many are being written.
        goniometer (Dict[str, Any] Goniometer geometry description.
        detector (Dict[str, Any]): Detector specific parameters and its axes.
        module (Dict[str, Any]): Geometry and description of detector module.
        source (Dict[str, Any]): Facility information.
        beam (Dict[str, Any]): Beam properties.
        attenuator (Dict[str, Any]): Attenuator properties.
        osc_scan (Dict[str, ArrayLike]): Axis defining the rotation scan. It should be passed even when still.
        transl_scan (Dict[str, ArrayLike], optional): Axes defining a linear or 2D scan. Defaults to None.
        metafile (Path | str, optional): File containing the metadata. Defaults to None.
        link_list (List, optional): List of datasets that can be copied from the metafile. Defaults to None.
        sample_depends_on (str, optional): Axis on which the sample depends on. Defaults to None.
    """
    logger = logging.getLogger("nexgen.Call")
    logger.setLevel(logging.DEBUG)
    logger.info("Calling the writers ...")

    # Split vectors and offsets in goniometer and detector for writing
    reframe_arrays(
        goniometer,
        detector,
        module,
        coordinate_frame,
    )

    # Check that filenames are paths
    if all(isinstance(f, Path) for f in datafiles) is False:
        datafiles = [Path(f).expanduser().resolve() for f in datafiles]

    if metafile:
        if type(metafile) is str:
            metafile = Path(metafile).expanduser().resolve()

    # NXdata: entry/data
    write_NXdata(
        nxsfile,
        datafiles,
        goniometer,
        data_type[0],
        osc_scan,
        transl_scan,
    )

    # NXinstrument: entry/instrument
    write_NXinstrument(
        nxsfile,
        beam,
        attenuator,
        source,
    )

    # NXdetector: entry/instrument/detector
    write_NXdetector(
        nxsfile,
        detector,
        data_type,
        metafile,
        link_list,
    )

    # NXmodule: entry/instrument/detector/module
    write_NXdetector_module(
        nxsfile,
        module,
        detector["image_size"],  # [::-1],
        detector["pixel_size"],
        beam_center=detector["beam_center"],
    )

    # NXsource: entry/source
    write_NXsource(nxsfile, source)

    # NXsample: entry/sample
    write_NXsample(
        nxsfile,
        goniometer,
        data_type[0],
        osc_scan,
        transl_scan,
        sample_depends_on,
    )


# Write NeXus directly from scope_extract
def write_nexus_from_scope(
    nxs_file: h5py.File,
    goniometer: ScopeExtract,
    detector: ScopeExtract,
    module: ScopeExtract,
    beam: ScopeExtract,
    attenuator: ScopeExtract,
    source: ScopeExtract,
    coordinate_frame: str = "mcstas",
    datafiles: List[Path] = None,
    data_type: Tuple[str, int] = None,
    **params,
):
    """
    Write a new NXmx NeXus file taking scope extracts as input.

    This function writes either a NeXus file for an existing dataset or a demo NeXus file with a blank dataset using the information passed from phil parameters.

    Args:
        nxs_file (h5py.File): NeXus file handle
        goniometer (freephil.common.scope_extract): Scope extract defining the goniometer geometry.
        detector (freephil.common.scope_extract): Scope extract defining the detector and its axes.
        module (freephil.common.scope_extract): Scope extract defining defining geometry and description of module.
        beam (freephil.common.scope_extract): Scope extract defining properties of beam.
        attenuator (freephil.common.scope_extract): Scope extract defining transmission.
        source (freephil.common.scope_extract): Scope extract describing the facility.
        coordinate_frame (str, optional): Coordinate system used to define the vectors. Defaults to "mcstas".
        datafiles (List[Path], optional): HDF5 data files from an existing collection. Defaults to None.
        data_type (Tuple[str, int], optional): Description of the data and eventually how many images make up the dataset. Defaults to None.

    Keyword arguments (**params):
        meta (Tuple[Path | str, List | None]): Metafile information, path to _meta.h5 file and eventual list of values not to look for in it.
        vds (str): If passed, a Virtual DataSet will be written. Accepted values: "dataset", "file".
        tristanSpec (freephil.common.scope_extract): Scope extract defining properties of a Tristan detector.
        timestamps (Tuple[datetime.datetime | None]): Start and end time of the collection, if known. Passed as datetime.datetime.
        notes (Tuple[str, Dict]): Any eventual notes that would be worth recording in the NeXus file.

    Raises:
        ValueError: If data_type has not been passed when writing blank data.
    """
    writer_logger = logging.getLogger("nexgen.WritefromScope")
    writer_logger.setLevel(logging.DEBUG)

    writer_logger.info("Write NXmx NeXus file from scope extract input.")

    # Check if it's a NeXus file for an existing collection or a new blank dataset.
    # And define data_type
    if datafiles:
        writer_logger.info("Writing a NeXus file for an existing collection")
        if detector.mode == "events":
            data_type = ("events", None)
            writer_logger.info("Data type: events.")
        else:
            # Find total number of images that have been written across the files.
            if len(datafiles) == 1:
                with h5py.File(datafiles[0], "r") as f:
                    num_images = f["data"].shape[0]
            else:
                num_images = find_number_of_images(datafiles)
            data_type = ("images", num_images)
            writer_logger.info(
                "Data type: images. \n" f"Total number of images: {num_images}"
            )
    else:
        writer_logger.warning("No data files have been passed.")
        writer_logger.info("Writing a demo NeXus file with blank data.")
        if data_type is None:
            writer_logger.error(
                "When writing a demo with blank data, a data_type tuple should be passed."
                "data_type is a Tuple[str, int | None],"
                "It should cointain a string indicating whether images or events are being written and eventually the number of images."
            )
            raise ValueError(
                "Missing data type information."
                "Please pass the type of data being written ('images'/'events') and eventually the number of images."
            )

    # Log goniometer information
    writer_logger.info("Goniometer information")
    for j in reversed(range(len(goniometer.axes))):
        vector = goniometer.vectors[3 * j : 3 * j + 3]
        writer_logger.info(
            f"Goniometer axis: {goniometer.axes[j]} => {vector} ({goniometer.types[j]}) on {goniometer.depends[j]}. {goniometer.starts[j]} {goniometer.ends[j]} {goniometer.increments[j]}"
        )
    writer_logger.info("\n")

    # Define rotation and translation axes
    OSC, TRANSL = ScanReader(
        goniometer.__dict__,
        data_type[0],
        n_images=data_type[1],
        snaked=params["snaked"] if "snaked" in params.keys() else True,
    )

    # Log scan information
    writer_logger.info("Coordinate system: %s" % coordinate_frame)
    writer_logger.info(f"Rotation scan axis: {list(OSC.keys())[0]}.")
    writer_logger.info(
        f"Scan from {list(OSC.values())[0][0]} to {list(OSC.values())[0][-1]}.\n"
    )
    if TRANSL:
        writer_logger.info(f"Scan along the {list(TRANSL.keys())} axes.")
        for k, v in TRANSL.items():
            writer_logger.info(f"{k} scan from {v[0]} to {v[-1]}.")
    writer_logger.info("\n")

    # Fix the number of images if not already there
    if data_type[0] == "images" and data_type[1] is None:
        data_type = ("images", len(list(OSC.values())[0]))
        writer_logger.warning(f"Total number of images updated to: {data_type[1]} \n")

    # If writing blank data, figure out how many files will need to be written
    if not datafiles:
        writer_logger.info("Calculating number of files to write ...")
        if data_type[0] == "events":
            # Determine the number of files. Write one file per module.
            n_files = 10 if "10M" in detector.description.upper() else 2
        else:
            # The maximum number of images being written each dataset is 1000
            if data_type[1] <= 1000:
                n_files = 1
            else:
                n_files = int(np.ceil(data_type[1] / 1000))

        writer_logger.info(
            f"{n_files} file(s) containing blank {data_type[0]} data to be written."
        )

        # Get datafile list
        datafile_template = get_filename_template(
            Path(nxs_file.filename).expanduser().resolve()
        )
        datafiles = [
            Path(datafile_template % (n + 1)).expanduser().resolve()
            for n in range(n_files)
        ]

        writer_logger.info("Calling data writer ...")
        # Write data files
        if data_type[0] == "images":
            generate_image_files(
                datafiles, detector.image_size, detector.description, data_type[1]
            )
        else:
            exp_time = units_of_time(detector.exposure_time)
            generate_event_files(
                datafiles, data_type[1], detector.description, exp_time.magnitude
            )

    # If _meta.h5 file is passed, look through it for relevant information
    if "meta" in params.keys():
        writer_logger.info("Looking through _meta.h5 file for metadata.")
        metafile = (
            Path(params["meta"]).expanduser().resolve()
            if isinstance(params["meta"], str) is False
            else params["meta"]
        )
        do_not_link = params["ignore_meta"]
        # overwrite detector, overwrite beam, get list of links for nxdetector and nxcollection
        with h5py.File(metafile, "r", libver="latest", swmr=True) as mf:
            overwrite_beam(mf, detector.description, beam)
            link_list = overwrite_detector(mf, detector, do_not_link)
    else:
        writer_logger.info("No _meta file has been passed.")
        metafile = None
        link_list = None

    # Log detector information
    if "TRISTAN" in detector.description.upper() and "tristanSpec" in params.keys():
        from ..command_line import add_tristan_spec

        add_tristan_spec(detector, params["tristanSpec"])

    writer_logger.info("Detector information")
    writer_logger.info(f"{detector.description}")
    writer_logger.info(
        f"Sensor made of {detector.sensor_material} x {detector.sensor_thickness}"
    )
    if data_type[0] == "images":
        writer_logger.info(
            f"Trusted pixels > {detector.underload} and < {detector.overload}"
        )
    writer_logger.info(
        f"Image is a {detector.image_size} array of {detector.pixel_size} pixels"
    )

    writer_logger.info("Detector axes:")
    for j in range(len(detector.axes)):
        vector = detector.vectors[3 * j : 3 * j + 3]
        writer_logger.info(
            f"Detector axis: {detector.axes[j]} => {vector} ({detector.types[j]}) on {detector.depends[j]}. {detector.starts[j]}"
        )

    if detector.flatfield is None:
        writer_logger.info("No flatfield applied")
    else:
        writer_logger.info(f"Flatfield correction data lives here {detector.flatfield}")

    if detector.pixel_mask is None:
        writer_logger.info("No bad pixel mask for this detector")
    else:
        writer_logger.info(f"Bad pixel mask lives here {detector.pixel_mask}")

    writer_logger.info("Module information")
    writer_logger.warning(f"module_offset field setting: {module.module_offset}")
    writer_logger.info(f"Number of modules: {module.num_modules}")
    writer_logger.info(f"Fast axis at datum position: {module.fast_axis}")
    writer_logger.info(f"Slow_axis at datum position: {module.slow_axis} \n")

    # Log source information
    writer_logger.info("Source information")
    writer_logger.info(f"Facility: {source.name} - {source.type}.")
    writer_logger.info(f"Beamline: {source.beamline_name} \n")

    # Start writing NeXus file
    write_NXentry(nxs_file)

    # Call the writers
    call_writers(
        nxs_file,
        datafiles,
        coordinate_frame,
        data_type,
        goniometer.__dict__,
        detector.__dict__,
        module.__dict__,
        source.__dict__,
        beam.__dict__,
        attenuator.__dict__,
        OSC,
        TRANSL,
        metafile,
        link_list,
    )

    # Write VDS if prompted
    if "vds" in params.keys():
        if data_type[0] == "images" and params["vds"] == "dataset":
            writer_logger.info(
                "Calling VDS writer to write a Virtual Dataset under /entry/data/data"
            )
            image_vds_writer(nxs_file, (data_type[1], *detector.image_size))
        elif data_type[0] == "images" and params["vds"] == "file":
            writer_logger.info(
                "Calling VDS writer to write a Virtual Dataset file and relative link."
            )
            vds_file_writer(nxs_file, datafiles, (data_type[1], *detector.image_size))
        else:
            writer_logger.info("VDS won't be written.")

    # Write timestamps if prompted
    if "timestamps" in params.keys():
        timestamps = params["timestamps"]
        writer_logger.info("Writing recorded timestamps.")
        # NX_DATE_TIME: /entry/start_time and /entry/end_time
        if timestamps[0] is not None:
            write_NXdatetime(nxs_file, (timestamps[0], None))
        if timestamps[1] is not None:
            write_NXdatetime(nxs_file, (None, timestamps[1]))

    # Write any notes that might have been passed as NXnote
    if "notes" in params.keys():
        writer_logger.info(
            f"Writing NXnote in requested location {params['notes'][0]}."
        )
        write_NXnote(nxs_file, params["notes"][0], params["notes"][1])
