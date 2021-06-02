"""
"""
import sys
import h5py
import numpy as np

# from pathlib import Path

from . import find_scan_axis
from .. import create_attributes

# NXdata writer
def write_NXdata(
    nxsfile: h5py.File,
    datafiles: list,
    goniometer: dict,
    data_type: str,
    scan_axis=None,
):
    """
    Args:
        nxsfile:
        datafiles:   List of Path objects
        goniometer: Dictionary
        data_type:
        image_size:
        scan_axis:
        N:          Number of images or of events, defaults to None.
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
    # idx = goniometer.axes.index(scan_axis)
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

    # 5 - write nxdata with attributes
    # 6 - write scan axis dataset


# NXsample
def write_NXsample(nxsfile: h5py.File, goniometer: dict):
    # 1 - check whether file already has nxentry, if it doesn't create it
    # 2 - create nxsample with attributes
    # 3 - look for nxbeam in file, if there make link
    # 4 - write sample_depends_on
    # 5 - create nxtransformation
    # 6 - determine scan axis
    # 7 - try: make a link to scan axis in nxdata
    # 7 - if it doesn't exist, write here
    # 8 - write sample_ groups from goniometer (only angles)
    # 9 - write links to sample_ in transformations
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
    # 4 - write NXbeam
    # 6 - call write_NXdetector
    # 7 - call write_NXpositioner
    pass


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
def write_NXdetector(nxsfile: h5py.File, detector: dict):
    # 1 - checke whether nxinstrument exists, if not create it
    # 2 - create nxdetector group with attribute
    # 3 - write all datasets
    # 4- check for mask and flatfield files
    # 5 - if images write overload and underload
    # 6 - call write_NXmodule
    # 7 - call write_NXcollection
    pass


# NXdetector_module writer
def write_NXmodule(nxdetector: h5py.Group, module: dict):
    # 1- create nxdetectormodule group
    # 2 - check how many modules
    # 3 - write relevant datasets
    # 4 - if module_offset is True, calculate and write it
    # 4 - and correct dependency tree accordingly
    pass


# NXpositioner (det_z and 2theta)
def write_NXpositioner(nxinstrument: h5py.Group, detector: dict):
    # 1 - write detector_z
    # 2 - write entry/instrument/transformation with link to det_z
    # 3 - add 2 theta arm if there and add link in transformations
    pass


# NXCollection writer (detectorSpecific)
def write_NXcollection(nxdetector: h5py.Group, detector: dict, n_images=None):
    # 1 - create detectorSpecific group
    # 2 - write x_pixels and y_pixels
    # 3 - if images write n_images
    # 4 - if events write tick time and frequency
    pass
