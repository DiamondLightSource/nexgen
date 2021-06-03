"""
"""
import sys
import h5py
import numpy as np

# from pathlib import Path

from . import find_scan_axis, split_arrays
from .. import create_attributes, set_dependency

# FIXME check that if group exists, it has the correct attributes

# NXdata writer
def write_NXdata(
    nxsfile: h5py.File,
    datafiles: list,
    goniometer: dict,
    data_type: str,
    coord_frame,
    scan_range,
    scan_axis=None,
):
    """
    Write NXdata group at entry/data

    Args:
        nxsfile:
        datafiles:   List of Path objects
        goniometer: Dictionary
        data_type:
        coord_frame:
        scan_axis:
        scan_range:
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
    scan_axis: str,
    scan_range=None,
):
    """
    Write NXsample group at entry/sample

    Args:
        nxsfile:
        goniometer:
        coord_frame:
        scan_axis:
        scan_range:
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
            try:
                for k in nxsfile["entry/data"].keys():
                    if nxsfile["entry/data"][k].attrs.get("depends_on"):
                        nxsample_ax[ax] = nxsfile[nxsfile["entry/data"][k].name]
                        nxtransformations[ax] = nxsfile[nxsfile["entry/data"][k].name]
            except KeyError:
                idx = goniometer["axes"].index(scan_axis)
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
            increment_set = np.repeat(goniometer["increments"][idx], len(scan_range))
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
        nxsfile:
        beam:
        attenuator:
        detector:
        beamline_n:
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
def write_NXsource(nxsfile: h5py.File, source):
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
def write_NXdetector(nxsfile: h5py.File, detector: dict, n_images=None):
    """
    Write_NXdetector group at entry/instrument/detector

    Args:
        nxsfile:
        detector:
        n_images:   Number of written images (for image mode detector)
    """
    # 1 - checke whether nxinstrument exists, if not create it
    # 2 - create nxdetector group with attribute
    # 3 - write all datasets
    # 4- check for mask and flatfield files
    # 5 - if images write overload and underload
    # 6 - call write_NXmodule
    # 7 - call write_NXcollection
    # 8 - write transformations with links to detector_z and two_theta
    pass


# NXdetector_module writer
def write_NXdetector_module(nxsfile: h5py.File, module: dict, image_size, pixel_size):
    """
    Write NXdetector_module group at entry/instrument/detector/module.

    Args:
        nxsfile:
        module:
        image_size:
        pixel_size:
    """
    # 1- create nxdetectormodule group
    # 2 - check how many modules
    # 3 - write relevant datasets
    # 4 - if module_offset is True, calculate and write it
    # 4 - and correct dependency tree accordingly
    pass


# NXdetector_group writer
# def writr_NXdetector_group(nxinstrument: h5py.Group, detector: dict):
# TODO to be added once multiple module functionality works
# pass


# NXCollection writer (detectorSpecific)
def write_NXcollection(nxdetector: h5py.Group, image_size, n_images=None):
    """
    Write a NXcollection group inside NXdetector as detectorSpecific.
    """
    # 1 - create detectorSpecific group
    # 2 - write x_pixels and y_pixels
    # 3 - if images write n_images
    # 4 - if events write tick time and frequency
    pass


# NXpositioner (det_z and 2theta)
# def write_NXpositioner(nxinstrument: h5py.Group, detector: dict):
# 1 - write detector_z
# 2 - add 2 theta arm if there
#    pass
