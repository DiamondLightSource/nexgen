"""
General tools to copy metadata from NeXus files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import h5py

from ..nxs_write.write_utils import create_attributes
from ..utils import get_nexus_filename
from .copy_utils import get_nexus_tree

copy_logger = logging.getLogger("nexgen.CopyNeXus")


def images_nexus(
    data_file: List[Path | str],
    original_nexus: Path | str,
    simple_copy: bool = True,
    skip_group: List[str] = ["NXdata"],
) -> str:
    """
    Copy NeXus metadata for images.

    Args:
        data_file (List[Path  |  str]): HDF5 file with images.
        original_nexus (Path  |  str): Original NeXus file with experiment metadata.
        simple_copy (bool, optional): Copy everything from the original NeXus file. Defaults to True.
        skip_group (List[str], optional): If simple_copy is False, list of NX_class objects to skip when copying.
                                        Defaults to ["NXdata"].

    Returns:
        nxs_filename (str): Filename of new NeXus file.
    """
    copy_logger.info("Copying NeXus file for image dataset ...")
    data_file = [Path(d).expanduser().resolve() for d in data_file]
    original_nexus = Path(original_nexus).expanduser().resolve()
    nxs_filename = get_nexus_filename(data_file[0], copy=True)
    copy_logger.debug(f"New NeXus file name: {nxs_filename}")
    with h5py.File(original_nexus, "r") as nxs_in, h5py.File(nxs_filename, "x") as nxs_out:
        if simple_copy is True:
            # Copy the whole tree
            get_nexus_tree(nxs_in, nxs_out, skip=False)
        else:
            copy_logger.warning(
                f"The following NX base classes will not be copied: {skip_group}"
            )
            nxs_out.attrs["default"] = "entry"
            # Copy the whole tree except for nxdata and whatever other group was passed.
            nxentry = get_nexus_tree(nxs_in, nxs_out, skip=True, skip_obj=skip_group)
            copy_logger.debug(f"Re write NXdata with link to {data_file[0]}.")
            if "NXdata" in skip_group:  # it always is...
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
    return nxs_filename.as_posix()


def pseudo_events_nexus(
    data_file: List[Path | str],
    original_nexus: Path | str,
) -> str:
    """
    Copy NeXus metadata for pseudo event mode data.

    Args:
        data_file (List[Path  |  str]): HDF5 with pseud event data.
        original_nexus (Path  |  str): Original NeXus file with experiment metadata.

    Returns:
        nxs_filename (str): Filename of new NeXus file.
    """
    copy_logger.info("Copying NeXus file for events dataset ...")
    data_file = [Path(d).expanduser().resolve() for d in data_file]
    original_nexus = Path(original_nexus).expanduser().resolve()
    nxs_filename = get_nexus_filename(data_file[0], copy=True)
    copy_logger.debug(f"New NeXus file name: {nxs_filename}")
    with h5py.File(original_nexus, "r") as nxs_in, h5py.File(
        nxs_filename, "x"
    ) as nxs_out:
        nxs_out.attrs["default"] = "entry"
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
    return nxs_filename.as_posix()
