"""
General tools to copy metadata from NeXus files.
"""

import h5py

from pathlib import Path
from typing import Union, Optional

from . import get_nexus_tree
from ..nxs_write import create_attributes


def images_nexus(
    data_file: Optional[Union[Path, str]],
    original_nexus: Optional[Union[Path, str]],
    simple_copy: bool = False,
):
    """
    Copy NeXus metadata for images.

    Args:
        data_file:       String or Path pointing to the HDF5 file with images.
        original_nexus:  String or Path pointing to the NeXus file with experiment metadata.
        simple_copy:     Defaults False. If passed, copy everything directly.
    """
    data_file = Path(data_file).expanduser().resolve()
    original_nexus = Path(original_nexus).expanduser().resolve()
    nxs_filename = data_file.parent / f"{data_file.stem}.nxs"
    with h5py.File(original_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, "x"
    ) as nxs_out:
        if simple_copy is True:
            # Copy the whole tree including nxdata
            get_nexus_tree(nxs_in, nxs_out, skip=False)
        else:
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
            with h5py.File(data_file, "r") as fout:
                nxdata["data"] = h5py.ExternalLink(fout.filename, "data")


def pseudo_events_nexus(
    data_file: Optional[Union[Path, str]],
    original_nexus: Optional[Union[Path, str]],
):
    """
    Copy NeXus metadata for pseudo event mode data.

    Args:
        data_file:       String or Path pointing to the HDF5 file with pseudo event data.
        original_nexus:  String or Path pointing to the NeXus file with experiment metadata.
    """
    data_file = Path(data_file).expanduser().resolve()
    original_nexus = Path(original_nexus).expanduser().resolve()
    nxs_filename = data_file.parent / f"{data_file.stem}.nxs"
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
        with h5py.File(data_file, "r") as fout:
            for k in fout.keys():
                nxdata[k] = h5py.ExternalLink(fout.filename, k)
