"""
Writer functions for different groups of a NeXus file.
"""
import sys
import h5py
import numpy as np

from . import find_scan_axis, split_arrays, calculate_origin
from .. import create_attributes, set_dependency, imgcif2mcstas

# FIXME check that if group exists, it has the correct attributes
# FIXME for event data the scan axis should only have a tuple (start, end)

# NXdata writer
def write_NXdata(
    nxsfile: h5py.File,
    datafiles: list,
    goniometer: dict,
    data_type: str,
    coord_frame: str,
    scan_range,
    scan_axis=None,
):
    """
    Write NXdata group at entry/data

    Args:
        nxsfile:        NeXus file to be written
        datafiles:      List of Path objects
        goniometer:     Dictionary containing all the axes information
        data_type:      Images or events
        coord_frame:    Coordinate system the axes are currently in
        scan_axis:      Rotation axis
        scan_range:     If writing events, this is just a (start, end) tuple
    """
    # Check that a valid datafile_list has been passed.
    assert len(datafiles) > 0, "Please pass at least a list of one HDF5 data file."

    # If scan_axis hasn't been passed, identify it.
    if not scan_axis:
        scan_axis = find_scan_axis(
            goniometer["axes"], goniometer["starts"], goniometer["ends"]
        )

    # Create NXdata group, unless it already exists, in which case just open it.
    try:
        nxdata = nxsfile.create_group("entry/data")
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
        nxdata = nxsfile["entry/data"]

    # If mode is images, link to blank image data. Else go to events.
    if data_type == "images":
        if len(datafiles) == 1:
            nxdata["data"] = h5py.ExternalLink(datafiles[0].name, "data")
        else:
            for filename in datafiles:
                # TODO write vds
                nxdata[filename.stem] = h5py.ExternalLink(filename.name, "data")
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
    # FIXME temporary quick way
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
    goniometer: dict,
    coord_frame: str,
    data_type: str,
    scan_axis: str,
    scan_range=None,
):
    """
    Write NXsample group at entry/sample

    Args:
        nxsfile:        NeXus file to be written
        goniometer:     Dictionary containing all the axes information
        coord_frame:    Coordinate system the axes are currently expressed in
        scan_axis:      Rotation axis
        scan_range:     List/tuple/array of scan axis values
    """
    # Create NXsample group, unless it already exists, in which case just open it.
    try:
        nxsample = nxsfile.create_group("entry/sample")
        create_attributes(
            nxsample,
            ("NX_class",),
            ("NXsample",),
        )
    except ValueError:
        nxsample = nxsfile["entry/sample"]

    # Save sample depends_on
    nxsample.create_dataset("depends_on", data=set_dependency(goniometer["axes"][-1]))

    # Create NXtransformations group: /entry/sample/transformations
    try:
        nxtransformations = nxsample.create_group("transformations")
        create_attributes(
            nxsample,
            ("NX_class",),
            ("NXtransformations",),
        )
    except ValueError:
        nxtransformations = nxsample["transformations"]

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
                for k in nxsfile["entry/data"].keys():
                    if nxsfile["entry/data"][k].attrs.get("depends_on"):
                        nxsample_ax[ax] = nxsfile[nxsfile["entry/data"][k].name]
                        nxtransformations[ax] = nxsfile[nxsfile["entry/data"][k].name]
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
        nxsample["beam"] = nxsfile["entry/instrument/beam"]
    except KeyError:
        pass


# NXinstrument
def write_NXinstrument(
    nxsfile: h5py.File, beam: dict, attenuator: dict, detector: dict, beamline_n: str
):
    """
    Write NXinstrument group at entry/instrument.

    Args:
        nxsfile:    NeXus file to be written
        beam:       Dictionary with beam wavelength and flux
        attenuator: Dictionary containing transmission
        detector:   Dictionary containing all detector information
        beamline_n: String identisying the beamline number
    """
    # Create NXinstrument group, unless it already exists, in which case just open it.
    try:
        nxinstrument = nxsfile.create_group("entry/instrument")
        create_attributes(
            nxinstrument,
            ("NX_class",),
            ("NXinstrument",),
        )
    except ValueError:
        nxinstrument = nxsfile["entry/instrument"]

    # Write /name field and relative attribute
    nxinstrument.create_dataset(
        "name", data=np.string_("DIAMOND BEAMLINE " + beamline_n)
    )
    create_attributes(nxinstrument["name"], ("short_name",), ("DLS " + beamline_n,))

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
    flux = nxbeam.create_dataset("total_flux", data=beam["flux"])
    create_attributes(flux, ("units"), ("Hz",))

    # Write_NXpositioner: /entry/instrument/detector_z, two_theta
    # Not really needed, can be added later


# NXsource
def write_NXsource(nxsfile: h5py.File, source: dict):
    """
    Write NXsource group in entry/source.

    Args:
        nxsfile:    NeXus file where to write the group
        source:     Dictionary containing the facility information
    """
    try:
        nxsource = nxsfile.create_group("entry/source")
        create_attributes(
            nxsource,
            ("NX_class",),
            ("NXsource",),
        )
    except ValueError:
        nxsource = nxsfile["entry/source"]

    nxsource.create_dataset("name", data=np.string_(source["name"]))
    create_attributes(nxsource["name"], ("short_name",), (source["short_name"],))
    nxsource.create_dataset("type", data=np.string_(source["type"]))


# NXdetector writer
def write_NXdetector(
    nxsfile: h5py.File, detector: dict, coord_frame: str, n_images=None
):
    """
    Write_NXdetector group at entry/instrument/detector

    Args:
        nxsfile:        Nexus file to be written
        detector:       Dictionary containing all detector information
        coord_frame:    Coordinate system the axes are currently expressed in
        n_images:       Number of written images (for image mode detector)
    """
    # Create NXdetector group, unless it already exists, in which case just open it.
    try:
        nxdetector = nxsfile.create_group("entry/instrument/detector")
        create_attributes(
            nxdetector,
            ("NX_class",),
            ("NXdetector",),
        )
    except ValueError:
        nxdetector = nxsfile["entry/instrument/detector"]

    # Detector depends_on
    nxdetector.create_dataset(
        "depends_on", data="/entry/instrument/detector/transformations/det_z"
    )

    # Detector description
    nxdetector.create_dataset("description", data=np.string_(detector["description"]))
    nxdetector.create_dataset("type", data=np.string_("Pixel"))

    # Beam center
    beam_center_x = nxdetector.create_dataset(
        "beam_center_x", data=detector["beam_center"][0]
    )
    create_attributes(beam_center_x, ("units",), ("pixels",))
    beam_center_y = nxdetector.create_dataset(
        "beam_center_y", data=detector["beam_center"][1]
    )
    create_attributes(beam_center_y, ("units",), ("pixels",))

    # Pixel size
    x_pix_size = nxdetector.create_dataset(
        "x_pixel_size", data=detector["pixel_size"][0] / 1000
    )
    create_attributes(x_pix_size, ("units",), ("m",))
    y_pix_size = nxdetector.create_dataset(
        "y_pixel_size", data=detector["pixel_size"][1] / 1000
    )
    create_attributes(y_pix_size, ("units",), ("m",))

    # Count time
    nxdetector.create_dataset("count_time", data=detector["exposure_time"])

    # Sensor material, sensor thickness
    nxdetector.create_dataset(
        "sensor_material", data=np.string_(detector["sensor_material"])
    )
    nxdetector.create_dataset(
        "sensor_thickness", data=detector["sensor_thickness"] / 1000
    )
    create_attributes(nxdetector["sensor_thickness"], ("units",), ("m",))

    # If detector mode is images write overload and underload
    if detector["mode"] == "images":
        nxdetector.create_dataset("saturation_value", data=detector["overload"])
        nxdetector.create_dataset("underload_value", data=detector["underload"])

    # Check for mask and flatfield files
    # Flatfield
    if detector["flatfield"]:
        nxdetector.create_dataset("flatfield_applied", data=False)
        nxdetector.create_dataset("flatfield", data=detector["flatfield"])
    # Bad pixel mask
    if detector["pixel_mask"]:
        nxdetector.create_dataset("pixel_mask_applied", data=False)
        nxdetector.create_dataset("pixel_mask", data=detector["pixel_mask"])

    # Write_NXcollection
    write_NXcollection(nxdetector, detector["image_size"], n_images)

    # Write NXtransformations: entry/instrument/detector/transformations/detector_z and two_theta
    nxtransformations = nxdetector.create_group("transformations")
    create_attributes(
        nxtransformations,
        ("NX_class",),
        ("NXtransformations",),
    )

    # Create groups for detector_z and two_theta if present
    vectors = split_arrays(coord_frame, detector["axes"], detector["vectors"])

    # FIXME this assumes only detector_z or two_theta as axes
    for ax in detector["axes"]:
        idx = detector["axes"].index(ax)
        if ax == "det_z":
            grp_name = "detector_z"
            _dep = set_dependency(
                detector["depends"][idx],
                "entry/instrument/detector/transformations/two_theta/",
            )
        else:
            grp_name = ax
            _dep = set_dependency(
                detector["depends"][idx],
                "entry/instrument/detector/transformations/detector_z/",
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


# NXdetector_module writer
def write_NXdetector_module(
    nxsfile: h5py.File,
    module: dict,
    coord_frame: str,
    image_size,
    pixel_size,
    beam_center=None,
):
    """
    Write NXdetector_module group at entry/instrument/detector/module.

    Args:
        nxsfile:        Nexus file to be written
        module:         Dictionary containing the detector module information
        image_size:     Size of the detector
        pixel_size:     Size of the single pixels in fast and slow direction, in mm
        beam_center:    Only if origin needs to be calculated.
    """
    # Create NXdetector_module group, unless it already exists, in which case just open it.
    try:
        nxmodule = nxsfile.create_group("entry/instrument/detector/module")
        create_attributes(
            nxmodule,
            ("NX_class",),
            ("NXdetector_module",),
        )
    except ValueError:
        nxmodule = nxsfile["entry/instrument/detector/module"]

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
        # This is just to have the same type as after conversion
        fast_axis = tuple(module["fast_axis"])
        slow_axis = tuple(module["slow_axis"])

    offsets = split_arrays(coord_frame, ["fast_axis", "slow_axis"], module["offsets"])

    fast_pixel = nxmodule.create_dataset(
        "fast_pixel_direction", data=pixel_size[0] / 1000
    )
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
            offsets["fast_axis"],
            "mm",
            "translation",
            "mm",
            fast_axis,
        ),
    )

    slow_pixel = nxmodule.create_dataset(
        "slow_pixel_direction", data=pixel_size[1] / 1000
    )
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
            offsets["slow_axis"],
            "mm",
            "translation",
            "mm",
            slow_axis,
        ),
    )

    # If module_offset is set ti=o True, calculate and write it
    if module["module_offset"] is True:
        origin = calculate_origin(beam_center, pixel_size, fast_axis, slow_axis)
        # TODO correct value according to Jira tickets
        module_offset = nxmodule.create_dataset("module_offset", data=np.array([0, 0]))
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
                [0, 0, 0],  # origin,
                "mm",
                "translation",
                "mm",
                origin,  # [1, 0, 0],
            ),
        )
        # Correct dependency tree accordingly
        _path = "/entry/instrument/detector/module/module_offset"
        create_attributes(fast_pixel, ("depends_on"), (_path,))
        create_attributes(slow_pixel, ("depends_on"), (_path,))


# NXdetector_group writer
# def writr_NXdetector_group(nxinstrument: h5py.Group, detector: dict):
# TODO to be added once multiple module functionality works
# pass


# NXCollection writer (detectorSpecific)
def write_NXcollection(nxdetector: h5py.Group, image_size, n_images=None):
    """
    Write a NXcollection group inside NXdetector as detectorSpecific.

    Args:
        nxdetector:     HDF5 NXdetector group
        image_size:     Size of the detector
        n_images:       Number of images written per file.
    """
    # Create detectorSpecific group
    grp = nxdetector.create_group("detectorSpecific")
    grp.create_dataset("x_pixels", data=image_size[0])
    grp.create_dataset("y_pixels", data=image_size[1])
    if n_images is not None:
        grp.create_dataset("nimages", data=n_images)
    # TODO if images write n_images, if events write tick time and frequency


# NXpositioner (det_z and 2theta) - probably not needed
# def write_NXpositioner(nxinstrument: h5py.Group, detector: dict):
# 1 - write detector_z
# 2 - add 2 theta arm if there
#    pass
