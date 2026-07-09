"""
Tools to write Virtual DataSets
"""

import logging
from pathlib import Path

import h5py
import numpy as np
from numpy.typing import DTypeLike

from nexgen.tools.vds_tools import find_datasets_in_file

from .constants import jungfrau_fill_value, jungfrau_gap_size, jungfrau_mod_size

vds_logger = logging.getLogger("nexgen.VDSWriter")


def jungfrau_vds_writer(
    nxsfile: h5py.File,
    vds_shape: tuple | list,
    data_type: DTypeLike = np.uint16,
    source_dsets: list[str] | None = None,
):
    """Write VDS for Jungfrau 1M use case, with a tiled layout."""
    external_dsets = True
    entry_key = "data"
    frames = vds_shape[0]

    nxdata = nxsfile["/entry/data"]
    if not source_dsets:
        source_dsets = find_datasets_in_file(nxdata)
        external_dsets = False

    sources = []
    for dset in source_dsets:
        source_path = dset if external_dsets is True else "."
        source_name = entry_key if external_dsets is True else f"/entry/data/{dset}"
        source = h5py.VirtualSource(
            source_path, source_name, shape=(frames, *jungfrau_mod_size)
        )
        sources.append(source)

    layout = h5py.VirtualLayout(shape=vds_shape, dtype=data_type)
    # The first one is the upper one
    s0 = jungfrau_mod_size[0] + jungfrau_gap_size[0]
    layout[:, : jungfrau_mod_size[0], :] = sources[1][:, :, :]
    layout[:, s0:, :] = sources[0][:, :, :]

    nxdata.create_virtual_dataset(entry_key, layout, fillvalue=jungfrau_fill_value)


def vds_file_writer(
    nxsfile: h5py.File,
    datafiles: list[Path],
    data_shape: tuple | list,
    data_type: DTypeLike = np.uint16,
    entry_key: str = "data",
):
    """
    Write a Virtual DataSet _vds.h5 file for image data.

    Args:
        nxsfile (h5py.File): NeXus file being written.
        datafiles (list[Path]): list of paths to source files.
        data_shape (tuple | list): Shape of the dataset, usually defined as (num_frames, *image_size).
        data_type (DTypeLike, optional): Dtype. Defaults to np.uint16.
        entry_key (str): Entry key for the Virtual DataSet name. Defaults to data.
    """
    vds_logger.debug("Start creating VDS file ...")
    # Where the vds will go
    nxdata = nxsfile["/entry/data"]
    # entry_key = "data"

    # For every source dataset define its shape and number of frames
    # Once again, it is assumed that the maximum number of frames per dataset is 1000
    frames = (data_shape[0] // 1000) * [1000] + [data_shape[0] % 1000]
    sshape = [(f, *data_shape[1:]) for f in frames]

    # Create virtual layout
    layout = h5py.VirtualLayout(shape=data_shape, dtype=data_type)
    start = 0
    for n, filename in enumerate(datafiles):
        end = start + frames[n]
        vsource = h5py.VirtualSource(
            filename.name, entry_key, shape=sshape[n]
        )  # Source definition
        layout[start:end:1, :, :] = vsource
        start = end

    # Create a _vds.h5 file and add link to nexus file
    s = Path(nxsfile.filename).expanduser().resolve()
    vds_filename = s.parent / f"{s.stem}_vds.h5"
    del s
    with h5py.File(vds_filename, "w") as vds:
        vds.create_virtual_dataset("data", layout, fillvalue=-1)
    nxdata["data"] = h5py.ExternalLink(vds_filename.name, "data")
    vds_logger.debug(f"{vds_filename} written and link added to NeXus file.")


def clean_unused_links(
    nxsfile: h5py.File,
    vds_shape: tuple | list,
    start_index: int = 0,
):
    """
    Remove links to external data not used in VDS.

    Args:
        nxsfile (h5py.File): Handle to NeXus file being written.
        vds_shape (tuple | list): Actual shape of the VDS dataset, usually defined as (num_frames, *image_size).
        start_index(int): The start point for the source data. Defaults to 0.
    """
    vds_logger.debug("Cleaning links unused in VDS ...")
    # Location of the VDS
    nxdata = nxsfile["/entry/data"]
    dataset_names = find_datasets_in_file(nxdata)
    if len(dataset_names) == 1:
        vds_logger.debug("Only one linked file, no need to remove it.")
        return
    datasets = [nxdata[name] for name in dataset_names]
    dataset_lengths = [d.shape[0] for d in datasets]
    if sum(dataset_lengths) == vds_shape[0]:
        vds_logger.debug("All links are used in VDS, no need to remove any.")
        return
    for i, _ in enumerate(datasets):
        # unlink datasets before the start of VDS
        if sum(dataset_lengths[0 : i + 1]) < start_index:
            vds_logger.debug(f"Removing {dataset_names[i]} link.")
            del nxdata[dataset_names[i]]
        # unlink datasets after the end of VDS
        if sum(dataset_lengths[0:i]) > start_index + vds_shape[0]:
            vds_logger.debug(f"Removing {dataset_names[i]} link.")
            del nxdata[dataset_names[i]]
    vds_logger.debug("Links unused in VDS removed from NeXus file.")
