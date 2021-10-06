"""
General tools to copy metadata from NeXus files.
"""

import h5py

from pathlib import Path
from typing import Union, Optional, List

from . import get_nexus_tree
from .. import get_nexus_filename
from ..nxs_write import create_attributes


def images_nexus(
    data_file: List[Union[Path, str]],
    original_nexus: Optional[Union[Path, str]],
    simple_copy: bool = False,
    skip_group: List[str] = ["data"],
):
    """
    Copy NeXus metadata for images.

    Args:
        data_file:      String or Path pointing to the HDF5 file with images.
        original_nexus: String or Path pointing to the NeXus file with experiment metadata.
        simple_copy:    Defaults to False. If True, copy everything directly.
        skip_group:     If simple_copy is True, this is a list of the objects not to be copied.
                        For the moment, works only for NX_class objects.
    """
    data_file = [Path(d).expanduser().resolve() for d in data_file]
    original_nexus = Path(original_nexus).expanduser().resolve()
    nxs_filename = get_nexus_filename(data_file[0])
    with h5py.File(original_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, "x"
    ) as nxs_out:
        if simple_copy is True:
            # Copy the whole tree
            get_nexus_tree(nxs_in, nxs_out, skip=False)
        else:
            # Copy the whole tree except for nxdata
            nxentry = get_nexus_tree(nxs_in, nxs_out, skip=True, skip_obj=skip_group)
            # FIXME this needs some revision!
            if "data" in skip_group:
                # Create nxdata group
                nxdata = nxentry.create_group("data")
                # Find and copy only scan axis information
                for k in nxs_in["entry/data"].keys():
                    if "depends_on" in nxs_in["entry/data"][k].attrs.keys():
                        ax = k
                        nxs_in["entry/data"].copy(k, nxdata)
                create_attributes(
                    nxdata, ("NX_class", "axes", "signal"), ("NXdata", ax, "data")
                )
                # Add link to data
                if len(data_file) == 1:
                    nxdata["data"] = h5py.ExternalLink(data_file[0].name, "data")
                else:
                    for filename in data_file:
                        nxdata[filename.stem] = h5py.ExternalLink(filename.name, "data")
    return nxs_filename


def pseudo_events_nexus(
    data_file: List[Union[Path, str]],
    original_nexus: Optional[Union[Path, str]],
):
    """
    Copy NeXus metadata for pseudo event mode data.

    Args:
        data_file:       String or Path pointing to the HDF5 file with pseudo event data.
        original_nexus:  String or Path pointing to the NeXus file with experiment metadata.
    """
    data_file = [Path(d).expanduser().resolve() for d in data_file]
    original_nexus = Path(original_nexus).expanduser().resolve()
    nxs_filename = get_nexus_filename(data_file[0])
    with h5py.File(original_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, "x"
    ) as nxs_out:
        # Copy the whole tree except for nxdata
        nxentry = get_nexus_tree(nxs_in, nxs_out)
        # Create nxdata group
        nxdata = nxentry.create_group("data")
        # Find and copy only scan axis information
        for k in nxs_in["entry/data"].keys():
            if "depends_on" in nxs_in["entry/data"][k].attrs.keys():
                ax = k
                nxs_in["entry/data"].copy(k, nxdata)
        create_attributes(
            nxdata, ("NX_class", "axes", "signal"), ("NXdata", ax, "data")
        )
        # Add link to data
        if len(data_file) == 1:
            with h5py.File(data_file[0], "r") as fout:
                for k in fout.keys():
                    nxdata[k] = h5py.ExternalLink(fout.filename, k)
        else:
            for filename in data_file:
                nxdata[filename.stem] = h5py.ExternalLink(filename.name, "/")
    return nxs_filename


# TODO I should probably consider adding a link to vds in case there is one.
