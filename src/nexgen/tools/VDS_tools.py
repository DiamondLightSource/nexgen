"""
Tools to write Virtual DataSets
"""

import logging
from pathlib import Path
from typing import Any, List, Tuple, Union

import h5py
import numpy as np

vds_logger = logging.getLogger("NeXusGenerator.writer.vds")


def image_vds_writer(
    nxsfile: h5py.File,
    data_shape: Union[Tuple, List],
    data_type: Any = np.uint16,
):
    """
    Virtual DataSet writer function for image data.

    Args:
        nxsfile (h5py.File): NeXus file being written.
        data_shape (Union[Tuple, List]): Shape of the dataset, usually defined as (num_frames, *image_size).
        data_type (Any, optional): Dtype. Defaults to np.uint16.
    """
    vds_logger.info("Start creating VDS ...")
    # Where the vds will go
    nxdata = nxsfile["/entry/data"]
    entry_key = "data"
    # Look for the source datasets in the NeXus file.
    # FIXME for now this assumes that the source datasets are always links
    dsets = []
    for k in nxdata.keys():
        if isinstance(nxdata.get(k, getlink=True), h5py.ExternalLink):
            dsets.append(k)
    # For every source dataset define its shape and number of frames
    # Once again, it is assumed that the maximum number of frames per dataset is 1000
    frames = (data_shape[0] // 1000) * [1000] + [data_shape[0] % 1000]
    sshape = [(f, *data_shape[1:]) for f in frames]

    # Create virtual layout
    layout = h5py.VirtualLayout(shape=data_shape, dtype=data_type)
    start = 0
    for n, dset in enumerate(dsets):
        end = start + frames[n]
        vsource = h5py.VirtualSource(".", "/entry/data/" + dset, shape=sshape[n])
        layout[start:end:1, :, :] = vsource
        start = end

    # Writea Virtual Dataset in NeXus file
    nxdata.create_virtual_dataset(entry_key, layout, fillvalue=-1)
    vds_logger.info("VDS written to NeXus file.")


def vds_file_writer(
    nxsfile: h5py.File,
    datafiles: List[Path],
    data_shape: Union[Tuple, List],
    data_type: Any = np.uint16,
):
    """
    Write a Virtual DataSet _vds.h5 file for image data.

    Args:
        nxsfile (h5py.File): NeXus file being written.
        datafiles (List[Path]): List of paths to source files.
        data_shape (Union[Tuple, List]): Shape of the dataset, usually defined as (num_frames, *image_size).
        data_type (Any, optional): Dtype. Defaults to np.uint16.
    """
    vds_logger.info("Start creating VDS ...")
    # Where the vds will go
    nxdata = nxsfile["/entry/data"]
    entry_key = "data"

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
    vds_logger.info(f"{vds_filename} written and link added to NeXus file.")
