#!/usr/bin/env python

import os
import numpy
import h5py
from h5py import AttributeManager


def create_attributes(obj, names, values):
    for n, v in zip(names, values):
        if type(v) is str:
            v = numpy.string_(v)
        AttributeManager.create(obj, name=n, data=v)


# def get_nxdata():
#     pass


def copy_from_events():
    pass


def copy_from_images():
    pass


def copy_from_timepix(nxdata, step):
    # Timepix data have an array with start and stop value for rotation
    # instead of the full list.
    # If dealing with stills, start == stop
    for k in nxdata.keys():
        try:
            if type(nxdata[k]) is h5py.Dataset:
                scan_axis = k
                ax = nxdata[k]
        except KeyError:
            continue
    (start, stop) = ax[()]
    ax_range = numpy.array([round(p, 1) for p in numpy.arange(start, stop, step)])
    # Of course also sample/sample_ax/ax and sample/transformations/phi
    # # need to be changed
    return scan_axis, ax_range


def CopyNexusStructure(h5_out, h5_in, event_mode=False, flip=False):
    """
    Copy nexus tree from one file to another.
    """
    nxs_filename = os.path.splitext(h5_out)[0] + ".nxs"
    with h5py.File(h5_in, "r") as fin, h5py.File(nxs_filename, "x") as nxs:
        # Create first level with attributes
        nxentry = nxs.create_group("entry")
        create_attributes(nxentry, ("NX_class",), ("NXentry",))

        # Copy all of the nexus tree as it is except for /entry/data
        for k in fin["entry"].keys():
            if k == "data":
                continue
            fin["entry"].copy(k, nxentry)

        # Write NXdata group
        nxdata = nxentry.create_group("data")
        # Axes
        for k in fin["entry/data"].keys():
            if "data" in k:
                continue
            if "event" in k:
                continue
            fin["entry/data"].copy(k, nxdata)
            _ax = k
        create_attributes(
            nxdata, ("NX_class", "axes", "signal"), ("NXdata", _ax, "data")
        )
        # Add link to data
        try:
            fout = h5py.File(h5_out, "x")
            # img_to_h5(fout, fin)
            fin["entry/data"].copy("data", fout)  # Temporary fix
        except OSError:
            fout = h5py.File(h5_out, "r")

        if event_mode is True:
            for k in fout.keys():
                nxdata[k] = h5py.ExternalLink(fout.filename, k)
        else:
            nxdata["data"] = h5py.ExternalLink(fout.filename, "data")
        fout.close()

        # Flip data_size if prompted to do so
        # This is because in some Eiger HDF5 files "entry/instrument/detector/module/data_size" is flipped
        if flip is True:
            data_size = nxs["entry/instrument/detector/module/data_size"]
            data_size[...] = data_size[()][::-1]
