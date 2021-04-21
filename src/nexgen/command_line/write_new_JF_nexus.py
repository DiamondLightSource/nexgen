# import os
import sys

import h5py

import numpy as np

from nexgen import create_attributes


def find_scan_axis(gonio):
    # Dumb way
    for k in gonio.keys():
        if "increment" in k and gonio[k][()] != 0:
            return k.split("_")[0]


def calculate_module_offset(beam_center_xy, xy_pixel_size, fast_axis_v, slow_axis_v):
    # Scaled center
    x_scaled = beam_center_xy[0] * xy_pixel_size[0]
    y_scaled = beam_center_xy[1] * xy_pixel_size[1]
    # Detector origin
    det_origin = x_scaled * np.array(fast_axis_v) + y_scaled * np.array(slow_axis_v)
    det_origin = list(-det_origin)
    return det_origin


def main(infile: h5py.File, outfile: h5py.File):
    # Initiate NXentry in output file
    nxentry = outfile.create_group("entry")
    create_attributes(nxentry, ("NX_class",), ("NXentry",))

    # Copy definition (Nxmx)
    infile.copy("entry/definition", nxentry)

    # Start by figureing out which one is the scan axis
    ax = find_scan_axis(infile["entry/sample/goniometer"])

    # Data: /entry/data
    # Start by copying all data links, without attributes
    infile.copy("entry/data", nxentry, without_attrs=True)
    # Add scan axis w/ attributes
    infile["entry/sample/goniometer"].copy(ax, nxentry["data"], without_attrs=True)
    create_attributes(
        nxentry["data"][ax],
        ("depends_on", "transformation_type", "units", "vector"),
        (".", "rotation", "deg", [-1, 0, 0]),
    )  # TODO vector needs to be double checked
    # Write attributes
    create_attributes(
        nxentry["data"],
        ("NX_class", "axes", "signal"),
        ("NXdata", ax, "data"),
    )

    # Sample: /entry/sample
    nxsample = nxentry.create_group("sample")
    create_attributes(nxsample, ("NX_class",), ("NXsample",))
    # Copy beam as is, with attributes
    infile["entry/sample"].copy("beam", nxsample)
    # Write scan_axis with correct attributes (this is just a link)
    nxax = nxsample.create_group("sample_" + ax)
    create_attributes(nxax, ("NX_class",), ("NXpositioner",))
    nxax[ax] = outfile["entry/data/" + ax]
    # TODO also add increments, end etc ...
    for k in infile["entry/sample/goniometer"]:
        if ax in k and k != ax:
            infile["entry/sample/goniometer"].copy(k, nxax, without_attrs=True)
            create_attributes(nxax[k], ("units",), ("deg",))
    # Write NXtransformations (another link)
    nxtr = nxsample.create_group("transformations")
    create_attributes(nxtr, ("NX_class",), ("NXtransformations",))
    nxtr[ax] = outfile["entry/data/" + ax]
    # Write depends on
    nxsample.create_dataset(
        "depends_on", data=np.string_("/entry/sample/transformations/" + ax)
    )

    # Instrument: /entry/data/instrument
    nxinstrument = nxentry.create_group("instrument")
    create_attributes(nxinstrument, ("NX_class",), ("NXinstrument",))  # short_name ?
    # Copy JF1M (NXdetector_group) in full
    infile["entry/instrument"].copy("JF1M", nxinstrument)
    # Add NXsource
    nxsource = nxinstrument.create_group("source")
    create_attributes(nxsource, ("NX_class",), ("NXsource",))
    nxsource.create_dataset("name", data=np.string_("Diamond Light Source"))
    create_attributes(nxsource["name"], ("short_name",), ("DLS",))
    nxsource.create_dataset("type", data=np.string_("Synchrotron X-ray Source"))
    # Copy NXattenuator from filter
    infile["entry/instrument"].copy("filter", nxinstrument, name="attenuator")
    # Nxbeam is a link to the one in sample
    nxinstrument["beam"] = outfile["entry/sample/beam"]

    # Detector: /entry/data/instrument/detector
    nxdetector = nxinstrument.create_group("detector")
    create_attributes(nxdetector, ("NX_class",), ("NXdetector",))
    # What about detector depends_on dataset ?
    # Copy just the datasets
    for k in infile["entry/instrument/detector"].keys():
        if type(infile["entry/instrument/detector"]) is h5py.Dataset:
            infile["entry/instrument/detector"].copy(k, nxdetector)
    # Module: /entry/data/instrument/detector/module
    nxmodule = nxdetector.create_group("module")
    create_attributes(nxmodule, ("NX_class",), ("NXdetector_module",))

    # detectorSpecific
    # Finally copy detector mask in correct place
    nxdetector.create_dataset("pixel_mask_applied", data=False)  # might be true
    infile["entry/instrument/detector/detectorSpecific"].copy("pixel_mask", nxdetector)

    print("All done!")


if __name__ == "__main__":
    # Open files
    with h5py.File(sys.argv[1], "r") as fin, h5py.File(sys.argv[2], "x") as fout:
        main(fin, fout)