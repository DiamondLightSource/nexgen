"""
Tools to write Virtual DataSets
"""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, List, Tuple, Union
import itertools

import h5py
import numpy as np

vds_logger = logging.getLogger("nexgen.VDSWriter")


MAX_FRAMES_PER_DATASET = 1000


@dataclass
class Dataset:
    name: str
    source_shape: Tuple[int]  # The full shape of the source, regardless of start index
    dest_shape: Tuple[int]  # The shape of the destination, including the start_index
    start_index: int = 0  # The start index that we should start copying from


def find_datasets_in_file(nxdata):
    # Look for the source datasets in the NeXus file.
    # FIXME for now this assumes that the source datasets are always links
    dsets = []
    for k in nxdata.keys():
        if isinstance(nxdata.get(k, getlink=True), h5py.ExternalLink):
            dsets.append(k)
    return dsets


def split_into_datasets(data: int) -> List[int]:
    """Returns a list of dataset sizes given a number of frames.
    Assuming that the max frames per data set is 1000.
    e.g.
    >>> split_into_datasets(1150)
    >>> [1000, 150]
    """
    return (data // MAX_FRAMES_PER_DATASET) * [MAX_FRAMES_PER_DATASET] + [
        data % MAX_FRAMES_PER_DATASET
    ]


def get_start_idx_and_shape_per_dataset(
    data_shape: Tuple[int, int, int], start_idx: int = 0
) -> List[Tuple[int, Tuple[int, int, int]]]:
    """Splits the full data shape and start index up into values per dataset,
    given that each dataset has a maximum size.
    """
    if start_idx > data_shape[0]:
        raise ValueError(
            f"Start index {start_idx} must be less than full dataset length {data_shape[0]}"
        )
    if start_idx < 0:
        raise ValueError("Start index must be positive")

    start_idx_per_dset = split_into_datasets(start_idx)

    frames_per_dset = split_into_datasets(data_shape[0])
    shape_per_dset = [(f, *data_shape[1:]) for f in frames_per_dset]

    start_and_shape_per_dataset = itertools.zip_longest(
        start_idx_per_dset, shape_per_dset, fillvalue=0
    )

    return list(start_and_shape_per_dataset)


def create_virtual_layout(
    full_data_shape, dsets, start_and_shape_per_dataset, data_type, start_index
):
    """Create a virtual layout and populate it based on the provided data

    Args:
        full_data_shape (Union[Tuple, List]): The shape of the full dataset that we are copying from
        dsets (List[str]): The name of the datasets we're copying from
        start_and_shape_per_dataset (List[Tuple[int, Tuple[int, int, int]]]): The start index and shape of each dataset we're copying from
        data_type (Any): The datatype of the data to copy
    """
    layout = h5py.VirtualLayout(
        shape=(full_data_shape[0] - start_index, *full_data_shape[1:]), dtype=data_type
    )
    dest_start = 0
    for n, dset in enumerate(dsets):
        source_start, shape = start_and_shape_per_dataset[n]
        end = dest_start + shape[0] - source_start
        vsource = h5py.VirtualSource(".", "/entry/data/" + dset, shape=shape)
        layout[dest_start:end, :, :] = vsource[source_start : shape[0], :, :]
        dest_start = end

    return layout


def image_vds_writer(
    nxsfile: h5py.File,
    full_data_shape: Union[Tuple, List],
    start_index: int = 0,
    data_type: Any = np.uint16,
):
    """
    Virtual DataSet writer function for image data.

    Args:
        nxsfile (h5py.File): NeXus file being written.
        full_data_shape (Union[Tuple, List]): Shape of the full dataset, usually defined as (num_frames, *image_size).
        start_index(int): The start point for the source data
        data_type (Any, optional): Dtype. Defaults to np.uint16.
    """
    vds_logger.info("Start creating VDS ...")
    # Where the vds will go
    nxdata = nxsfile["/entry/data"]
    entry_key = "data"
    dsets = find_datasets_in_file(nxdata)

    start_and_shape_per_dataset = get_start_idx_and_shape_per_dataset(
        full_data_shape, start_index
    )

    layout = create_virtual_layout(
        full_data_shape, dsets, start_and_shape_per_dataset, data_type
    )

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
