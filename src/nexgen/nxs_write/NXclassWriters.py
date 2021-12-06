"""
Writer functions for different groups of a NeXus file.
"""

import sys
import h5py
import logging

import numpy as np

from pathlib import Path
from typing import List, Dict, Tuple, Union, Optional

from . import (
    find_scan_axis,
    calculate_origin,
    create_attributes,
    set_dependency,
)
from .. import (
    imgcif2mcstas,
    split_arrays,
    units_of_length,
    units_of_time,
    ureg,
)

from .data_tools import vds_writer

NXclass_logger = logging.getLogger("NeXusGenerator.write.NXclass")

# NXentry writer
def write_NXentry(nxsfile: h5py.File) -> h5py.Group:
    """
    Write NXentry group at top level of the NeXus file.
    Also, write the application definition NXmx.

    Args:
        nxsfile (h5py.File):    NeXus file handle

    Returns:
        NXentry group.
    """
    # Set default attribute
    nxsfile.attrs["default"] = "entry"

    # Start writing the NeXus tree with NXentry at the top level
    nxentry = nxsfile.create_group("entry")
    create_attributes(nxentry, ("NX_class", "default"), ("NXentry", "data"))

    # Application definition: /entry/definition
    nxentry.create_dataset("definition", data=np.string_("NXmx"))
    return nxentry


# NXdata writer
def write_NXdata(
    nxsfile: h5py.File,
    datafiles: List[Path],
    goniometer: Dict,
    data_type: str,
    coord_frame: str,
    scan_range: Union[Tuple, np.ndarray],
    scan_axis: str = None,
    write_vds: str = None,
):
    """
    Write NXdata group at entry/data

    Args:
        nxsfile (h5py.File):        NeXus file to be written
        datafiles (List):           List of Path objects
        goniometer (Dict):          Dictionary containing all the axes information
        data_type (str):            Images or events
        coord_frame (str):          Coordinate system the axes are currently in
        scan_range (Tuple|array):   If writing events, this is just a (start, end) tuple
        scan_axis (str):            Rotation axis
        write_vds (str):            If not None, writes a Virtual Dataset.
    """
    NXclass_logger.info("Start writing NXdata.")
    # Check that a valid datafile_list has been passed.
    assert len(datafiles) > 0, "Please pass at least a list of one HDF5 data file."

    # If scan_axis hasn't been passed, identify it.
    if not scan_axis:
        scan_axis = find_scan_axis(
            goniometer["axes"],
            goniometer["starts"],
            goniometer["ends"],
            goniometer["types"],
        )

    # Create NXdata group, unless it already exists, in which case just open it.
    try:
        nxdata = nxsfile.create_group("/entry/data")
        create_attributes(
            nxdata,
            ("NX_class", "axes", "signal", scan_axis + "_indices"),
            (
                "NXdata",
                scan_axis,
                "data",
                [
                    0,
                ],
            ),
        )
    except ValueError:
        nxdata = nxsfile["/entry/data"]

    # If mode is images, link to blank image data. Else go to events.
    if data_type == "images":
        if len(datafiles) == 1 and write_vds is None:
            nxdata["data"] = h5py.ExternalLink(datafiles[0].name, "data")
        elif len(datafiles) == 1 and write_vds:
            nxdata[datafiles[0].stem] = h5py.ExternalLink(datafiles[0].name, "data")
            NXclass_logger.info("Calling VDS writer.")
            vds_writer(nxsfile, datafiles, write_vds)
        else:
            for filename in datafiles:
                nxdata[filename.stem] = h5py.ExternalLink(filename.name, "data")
            if write_vds:
                NXclass_logger.info("Calling VDS writer.")
                vds_writer(nxsfile, datafiles, write_vds)
    elif data_type == "events":
        for filename in datafiles:
            nxdata[filename.stem] = h5py.ExternalLink(filename.name, "/")
    else:
        sys.exit("Please pass a correct data_type (images or events)")

    # Write rotation axis dataset
    ax = nxdata.create_dataset(scan_axis, data=scan_range)
    idx = goniometer["axes"].index(scan_axis)
    _dep = set_dependency(
        goniometer["depends"][idx], path="/entry/sample/transformations/"
    )

    vectors = split_arrays(coord_frame, goniometer["axes"], goniometer["vectors"])
    # Write attributes for axis
    create_attributes(
        ax,
        ("depends_on", "transformation_type", "units", "vector"),
        (
            _dep,
            goniometer["types"][idx],
            goniometer["units"][idx],
            vectors[scan_axis],
        ),
    )


# NXsample
def write_NXsample(
    nxsfile: h5py.File,
    goniometer: Dict,
    coord_frame: str,
    data_type: str,
    scan_axis: str,
    scan_range: Union[Tuple, np.ndarray] = None,
):
    """
    Write NXsample group at entry/sample

    Args:
        nxsfile (h5py.File):        NeXus file to be written
        goniometer (Dict):          Dictionary containing all the axes information
        coord_frame (str):          Coordinate system the axes are currently expressed in
        data_type (str):            Images or events
        scan_axis (str):            Rotation axis
        scan_range (Tuple|array):   List/tuple/array of scan axis values
    """
    NXclass_logger.info("Start writing NXsample and NXtransformations.")
    # Create NXsample group, unless it already exists, in which case just open it.
    try:
        nxsample = nxsfile.create_group("/entry/sample")
        create_attributes(
            nxsample,
            ("NX_class",),
            ("NXsample",),
        )
    except ValueError:
        nxsample = nxsfile["/entry/sample"]

    # Create NXtransformations group: /entry/sample/transformations
    try:
        nxtransformations = nxsample.create_group("transformations")
        create_attributes(
            nxtransformations,
            ("NX_class",),
            ("NXtransformations",),
        )
    except ValueError:
        nxtransformations = nxsample["transformations"]

    # Save sample depends_on
    nxsample.create_dataset(
        "depends_on", data=set_dependency(scan_axis, path=nxtransformations.name)
    )

    # Create sample_{axisname} groups
    vectors = split_arrays(coord_frame, goniometer["axes"], goniometer["vectors"])
    for ax in goniometer["axes"]:
        if "sam" in ax:
            grp_name = "sample_" + ax.split("_")[1]
        else:
            grp_name = "sample_" + ax
        nxsample_ax = nxsample.create_group(grp_name)
        create_attributes(nxsample_ax, ("NX_class",), ("NXpositioner",))
        if ax == scan_axis:
            # If we're dealing with the scan axis
            idx = goniometer["axes"].index(scan_axis)
            try:
                for k in nxsfile["/entry/data"].keys():
                    if nxsfile["/entry/data"][k].attrs.get("depends_on"):
                        nxsample_ax[ax] = nxsfile[nxsfile["/entry/data"][k].name]
                        nxtransformations[ax] = nxsfile[nxsfile["/entry/data"][k].name]
            except KeyError:
                nxax = nxsample_ax.create_dataset(ax, data=scan_range)
                _dep = set_dependency(
                    goniometer["depends"][idx], path="/entry/sample/transformations/"
                )
                create_attributes(
                    ax,
                    ("depends_on", "transformation_type", "units", "vector"),
                    (
                        _dep,
                        goniometer["types"][idx],
                        goniometer["units"][idx],
                        vectors[scan_axis],
                    ),
                )
                nxtransformations[ax] = nxsfile[nxax.name]
            # TODO handle the case where scan range has not been passed.
            # Write {axisname}_increment_set and {axis_name}_end datasets
            if data_type == "images":
                increment_set = np.repeat(
                    goniometer["increments"][idx], len(scan_range)
                )
                nxsample_ax.create_dataset(ax + "_increment_set", data=increment_set)
                nxsample_ax.create_dataset(ax + "_end", data=scan_range + increment_set)
        else:
            # For all other axes
            idx = goniometer["axes"].index(ax)
            nxax = nxsample_ax.create_dataset(ax, data=goniometer["starts"][idx])
            _dep = set_dependency(
                goniometer["depends"][idx], path="/entry/sample/transformations/"
            )
            create_attributes(
                nxax,
                ("depends_on", "transformation_type", "units", "vector"),
                (
                    _dep,
                    goniometer["types"][idx],
                    goniometer["units"][idx],
                    vectors[ax],
                ),
            )
            nxtransformations[ax] = nxsfile[nxax.name]

    # Look for nxbeam in file, if it's there make link
    try:
        nxsample["beam"] = nxsfile["/entry/instrument/beam"]
    except KeyError:
        pass


# NXinstrument
def write_NXinstrument(
    nxsfile: h5py.File, beam: Dict, attenuator: Dict, beamline_n: str
):
    """
    Write NXinstrument group at entry/instrument.

    Args:
        nxsfile (h5py.File):    NeXus file to be written
        beam (Dict):            Dictionary with beam wavelength and flux
        attenuator (Dict):      Dictionary containing transmission
        beamline_n (str):       String identisying the beamline number
    """
    NXclass_logger.info("Start writing NXinstrument.")
    # Create NXinstrument group, unless it already exists, in which case just open it.
    try:
        nxinstrument = nxsfile.create_group("/entry/instrument")
        create_attributes(
            nxinstrument,
            ("NX_class",),
            ("NXinstrument",),
        )
    except ValueError:
        nxinstrument = nxsfile["/entry/instrument"]

    # Write /name field and relative attribute
    NXclass_logger.info(f"DLS beamline {beamline_n}")
    nxinstrument.create_dataset(
        "name", data=np.string_("DIAMOND BEAMLINE " + beamline_n)
    )
    create_attributes(nxinstrument["name"], ("short_name",), ("DLS " + beamline_n,))

    NXclass_logger.info("Write NXattenuator and NXbeam.")
    # Write NXattenuator group: entry/instrument/attenuator
    nxatt = nxinstrument.create_group("attenuator")
    create_attributes(nxatt, ("NX_class",), ("NXattenuator",))
    nxatt.create_dataset(
        "attenuator_transmission",
        data=attenuator["transmission"],
    )

    # Write NXbeam group: entry/instrument/beam
    nxbeam = nxinstrument.create_group("beam")
    create_attributes(nxbeam, ("NX_class",), ("NXbeam",))
    wl = nxbeam.create_dataset("incident_wavelength", data=beam["wavelength"])
    create_attributes(wl, ("units",), ("angstrom",))
    if beam["flux"]:
        flux = nxbeam.create_dataset("total_flux", data=beam["flux"])
        create_attributes(flux, ("units"), ("Hz",))


# NXsource
def write_NXsource(nxsfile: h5py.File, source: Dict):
    """
    Write NXsource group in entry/source.

    Args:
        nxsfile (h5py.File):    NeXus file where to write the group
        source (Dict):          Dictionary containing the facility information
    """
    NXclass_logger.info("Start writing NXsource.")
    try:
        nxsource = nxsfile.create_group("/entry/source")
        create_attributes(
            nxsource,
            ("NX_class",),
            ("NXsource",),
        )
    except ValueError:
        nxsource = nxsfile["/entry/source"]

    nxsource.create_dataset("name", data=np.string_(source["name"]))
    create_attributes(nxsource["name"], ("short_name",), (source["short_name"],))
    nxsource.create_dataset("type", data=np.string_(source["type"]))


# NXdetector writer
def write_NXdetector(
    nxsfile: h5py.File,
    detector: Dict,
    coord_frame: str,
    data_type: Tuple[str, int],
    meta: Path = None,
    link_list: List = None,
):
    """
    Write_NXdetector group at entry/instrument/detector.

    Args:
        nxsfile (h5py.File):    Nexus file to be written.
        detector (Dict):        Dictionary containing all detector information.
        coord_frame (str):      Coordinate system the axes are currently expressed in.
        data_type (Tuple):      Tuple (str, int) identifying whether the files to be written contain images or events.
        meta (Path):            Path to _meta.h5 file, if exists.
        link_list (List):       List of values from the meta file to be linked instead of copied.
    """
    NXclass_logger.info("Start writing NXdetector.")
    # Create NXdetector group, unless it already exists, in which case just open it.
    try:
        nxdetector = nxsfile.create_group("/entry/instrument/detector")
        create_attributes(
            nxdetector,
            ("NX_class",),
            ("NXdetector",),
        )
    except ValueError:
        nxdetector = nxsfile["/entry/instrument/detector"]

    # Detector description
    nxdetector.create_dataset("description", data=np.string_(detector["description"]))
    nxdetector.create_dataset("type", data=np.string_(detector["detector_type"]))

    # If there is a meta file, a lot of information will be linked instead of copied
    if meta:
        for ll in link_list[0]:
            nxdetector[ll] = h5py.ExternalLink(meta.name, detector[ll])
    else:
        # Check for mask and flatfield files
        # Flatfield
        if detector["flatfield"]:
            nxdetector.create_dataset(
                "flatfield_applied", data=detector["flatfield_applied"]
            )
            nxdetector.create_dataset("flatfield", data=detector["flatfield"])
        # Bad pixel mask
        if detector["pixel_mask"]:
            nxdetector.create_dataset(
                "pixel_mask_applied", data=detector["pixel_mask_applied"]
            )
            nxdetector.create_dataset("pixel_mask", data=detector["pixel_mask"])
    try:
        # Beam center
        beam_center_x = nxdetector.create_dataset(
            "beam_center_x", data=detector["beam_center"][0]
        )
        create_attributes(beam_center_x, ("units",), ("pixels",))
        beam_center_y = nxdetector.create_dataset(
            "beam_center_y", data=detector["beam_center"][1]
        )
        create_attributes(beam_center_y, ("units",), ("pixels",))

        # Pixel size in m
        x_pix = units_of_length(detector["pixel_size"][0], True)
        x_pix_size = nxdetector.create_dataset("x_pixel_size", data=x_pix.magnitude)
        create_attributes(x_pix_size, ("units",), (format(x_pix.units, "~"),))
        y_pix = units_of_length(detector["pixel_size"][1], True)
        y_pix_size = nxdetector.create_dataset("y_pixel_size", data=y_pix.magnitude)
        create_attributes(y_pix_size, ("units",), (format(y_pix.units, "~"),))

        # Count time
        exp_time = units_of_time(detector["exposure_time"])
        nxdetector.create_dataset("count_time", data=exp_time.magnitude)

        # Sensor material, sensor thickness in m
        nxdetector.create_dataset(
            "sensor_material", data=np.string_(detector["sensor_material"])
        )
        sensor_thickness = units_of_length(detector["sensor_thickness"], True)
        nxdetector.create_dataset("sensor_thickness", data=sensor_thickness.magnitude)
        create_attributes(
            nxdetector["sensor_thickness"],
            ("units",),
            (format(sensor_thickness.units, "~"),),
        )

        # # Check for mask and flatfield files
        # # Flatfield
        # if detector["flatfield"]:
        #     nxdetector.create_dataset(
        #         "flatfield_applied", data=detector["flatfield_applied"]
        #     )
        #     nxdetector.create_dataset("flatfield", data=detector["flatfield"])
        # # Bad pixel mask
        # if detector["pixel_mask"]:
        #     nxdetector.create_dataset(
        #         "pixel_mask_applied", data=detector["pixel_mask_applied"]
        #     )
        #     nxdetector.create_dataset("pixel_mask", data=detector["pixel_mask"])
    except (TypeError, ValueError, RuntimeError):
        pass

    # If detector mode is images write overload and underload
    if data_type[0] == "images" and detector["overload"] is not None:
        nxdetector.create_dataset("saturation_value", data=detector["overload"])
        nxdetector.create_dataset("underload_value", data=detector["underload"])

    # Write_NXcollection
    write_NXcollection(nxdetector, detector, data_type, meta, link_list)

    # Write NXtransformations: entry/instrument/detector/transformations/detector_z and two_theta
    nxtransformations = nxdetector.create_group("transformations")
    create_attributes(
        nxtransformations,
        ("NX_class",),
        ("NXtransformations",),
    )

    # Create groups for detector_z and two_theta if present
    vectors = split_arrays(coord_frame, detector["axes"], detector["vectors"])

    # This assumes only detector_z or two_theta as axes, and that they are fixed.
    for ax in detector["axes"]:
        idx = detector["axes"].index(ax)
        if ax == "det_z":
            grp_name = "detector_z"
            _dep = set_dependency(
                detector["depends"][idx],
                nxtransformations.name + "/two_theta/",
            )
        else:
            grp_name = ax
            _dep = set_dependency(
                detector["depends"][idx],
                nxtransformations.name + "/detector_z/",
            )
        nxgrp_ax = nxtransformations.create_group(grp_name)
        create_attributes(nxgrp_ax, ("NX_class",), ("NXpositioner",))
        nxdet_ax = nxgrp_ax.create_dataset(ax, data=detector["starts"][idx])
        create_attributes(
            nxdet_ax,
            ("depends_on", "transformation_type", "units", "vector"),
            (
                _dep,
                detector["types"][idx],
                detector["units"][idx],
                vectors[ax],
            ),
        )
        if ax == detector["axes"][-1]:
            # Detector depends_on
            nxdetector.create_dataset(
                "depends_on",
                data=set_dependency(ax, path=nxgrp_ax.name),
            )


# NXdetector_module writer
def write_NXdetector_module(
    nxsfile: h5py.File,
    module: Dict,
    coord_frame: str,
    image_size: Union[List, Tuple],
    pixel_size: Union[List, Tuple],
    beam_center: Optional[Union[List, Tuple]] = None,
):
    """
    Write NXdetector_module group at entry/instrument/detector/module.

    Args:
        nxsfile (h5py.File):        Nexus file to be written
        module (Dict):              Dictionary containing the detector module information
        coord_frame (str):          Coordinate system the axes are currently expressed in.
        image_size (List|Tuple):    Size of the detector
        pixel_size (List|Tuple):    Size of the single pixels in fast and slow direction, in mm
        beam_center (List|Tuple):   Only if origin needs to be calculated.
    """
    NXclass_logger.info("Start writing NXdetector_module.")
    # Create NXdetector_module group, unless it already exists, in which case just open it.
    try:
        nxmodule = nxsfile.create_group("/entry/instrument/detector/module")
        create_attributes(
            nxmodule,
            ("NX_class",),
            ("NXdetector_module",),
        )
    except ValueError:
        nxmodule = nxsfile["/entry/instrument/detector/module"]

    # TODO check how many modules, and write as many, plus NXdetector_group
    nxmodule.create_dataset("data_origin", data=np.array([0, 0]))
    nxmodule.create_dataset("data_size", data=image_size)
    nxmodule.create_dataset("data_stride", data=np.array([1, 1]))

    # Write fast_ and slow_ pixel_direction
    # Convert vectors if needed
    if coord_frame == "imgcif":
        fast_axis = imgcif2mcstas(module["fast_axis"])
        slow_axis = imgcif2mcstas(module["slow_axis"])
    else:
        fast_axis = tuple(module["fast_axis"])
        slow_axis = tuple(module["slow_axis"])

    # offsets = split_arrays(coord_frame, ["fast_axis", "slow_axis"], module["offsets"])

    x_pix = units_of_length(pixel_size[0], True)
    fast_pixel = nxmodule.create_dataset("fast_pixel_direction", data=x_pix.magnitude)
    create_attributes(
        fast_pixel,
        (
            "depends_on",
            "offset",
            "offset_units",
            "transformation_type",
            "units",
            "vector",
        ),
        (
            "/entry/instrument/detector/transformations/detector_z/det_z",
            [0, 0, 0],
            # offsets["fast_axis"],
            "mm",
            "translation",
            format(x_pix.units, "~"),
            fast_axis,
        ),
    )

    y_pix = units_of_length(pixel_size[1], True)
    slow_pixel = nxmodule.create_dataset("slow_pixel_direction", data=y_pix.magnitude)
    create_attributes(
        slow_pixel,
        (
            "depends_on",
            "offset",
            "offset_units",
            "transformation_type",
            "units",
            "vector",
        ),
        (
            "/entry/instrument/detector/module/fast_pixel_direction",
            [0, 0, 0],
            # offsets["slow_axis"],
            "mm",
            "translation",
            format(y_pix.units, "~"),
            slow_axis,
        ),
    )

    # If module_offset is set to 1 or 2, calculate accordinlgy and write the field
    if module["module_offset"] != "0":
        pixel_size_m = [
            x_pix.magnitude,
            y_pix.magnitude,
        ]
        origin, offset_val = calculate_origin(
            beam_center,
            pixel_size_m,
            fast_axis,
            slow_axis,
            mode=module["module_offset"],
        )
        module_offset = nxmodule.create_dataset("module_offset", data=offset_val)
        create_attributes(
            module_offset,
            (
                "depends_on",
                "offset",
                "offset_units",
                "transformation_type",
                "units",
                "vector",
            ),
            (
                "/entry/instrument/detector/transformations/detector_z/det_z",
                [0, 0, 0],
                "mm",
                "translation",
                format(x_pix.units, "~"),
                origin,
            ),
        )

        # Correct dependency tree accordingly
        _path = "/entry/instrument/detector/module/module_offset"
        create_attributes(fast_pixel, ("depends_on"), (_path,))
        create_attributes(slow_pixel, ("depends_on"), (_path,))


# NXdetector_group writer
# def writr_NXdetector_group(nxinstrument: h5py.Group, detector: Dict):
# TODO to be added once multiple module functionality works
# pass


# NXCollection writer (detectorSpecific)
def write_NXcollection(
    nxdetector: h5py.Group,
    detector: Dict,
    data_type: Tuple[str, int],
    meta: Path = None,
    link_list: List = None,
    # nxdetector: h5py.Group, image_size: Union[List, Tuple], data_type: Tuple[str, int]
):
    """
    Write a NXcollection group inside NXdetector as detectorSpecific.

    Args:
        nxdetector (h5py.Group):    HDF5 NXdetector group.
        detector (Dict):            Dictionary containing all detector information
        data_type (Tuple[str,int]): Tuple identifying whether the files to be written contain images or events.
        meta (Path):                Path to _meta.h5 file, if exists.
        link_list (List):           List of values from the meta file to be linked instead of copied.
    """
    NXclass_logger.info("Start writing detectorSpecific group as NXcollection.")
    # Create detectorSpecific group
    grp = nxdetector.create_group("detectorSpecific")
    grp.create_dataset("x_pixels", data=detector["image_size"][0])
    grp.create_dataset("y_pixels", data=detector["image_size"][1])
    if data_type[0] == "images":
        grp.create_dataset("nimages", data=data_type[1])
    if meta:
        for l in link_list[1]:
            grp[l] = h5py.ExternalLink(meta.name, detector[l])
    else:
        if "software_version" in detector:
            grp.create_dataset(
                "software_version", data=np.string_(detector["software_version"])
            )
    if "TRISTAN" in detector["description"].upper():  # or data_type[1] == "events":
        tick = ureg.Quantity(detector["detector_tick"])
        grp.create_dataset("detector_tick", data=tick.magnitude)
        grp["detector_tick"].attrs["units"] = format(tick.units, "~")
        freq = ureg.Quantity(detector["detector_frequency"])
        grp.create_dataset("detector_frequency", data=freq.magnitude)
        grp["detector_frequency"].attrs["units"] = format(freq.units, "~")
        grp.create_dataset(
            "timeslice_rollover_bits", data=detector["timeslice_rollover"]
        )


# NXnote writer
# To be used e.g. as a place to store pump-probe info such as pump delay/width
def write_NXnote(nxsfile: h5py.File, loc: str, info: Dict):
    """
    Write any additional information as a NXnote class in a specified location in the NeXus file.

    Args:
        nxsfile (h5py.File):    Nexus file to be written.
        loc (str):              Location inside the NeXus file to write NXnote group.
        info (Dict):            Dictionary of datasets to be written to NXnote.
    """
    NXclass_logger.info("Start writing NXnote.")
    # Create the NXnote group in the specified location
    try:
        nxnote = nxsfile.create_group(loc)
        create_attributes(
            nxnote,
            ("NX_class",),
            ("NXnote",),
        )
    except ValueError:
        nxnote = nxsfile[loc]

    # Write datasets
    for k, v in info.items():
        if v:  # Just in case one value is not recorded and set as None
            if type(v) is str:
                v = np.string_(v)
            nxnote.create_dataset(k, data=v)
            NXclass_logger.info(f"{k} dataset writte in {loc}.")
