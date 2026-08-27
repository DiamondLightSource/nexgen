import logging
import operator
from functools import reduce
from typing import Sequence

import h5py
import numpy as np
from numpy.typing import DTypeLike
from pydantic.dataclasses import dataclass

from nexgen.tools.vds_tools.utils import find_datasets_in_file
from nexgen.utils import MAX_FRAMES_PER_DATASET

block_vds_logger = logging.getLogger("nexgen.tools.vds_tools.block_mapping")


@dataclass
class Dataset:
    name: str

    # The full shape of the source, regardless of start index
    source_shape: Sequence[int]

    # The start index that we should start copying from
    start_index: int = 0

    # The point where we should stop copying. Defaults to maximum for an Eiger
    stop_index: int = MAX_FRAMES_PER_DATASET

    # The shape of the destination, including the start_index
    dest_shape: Sequence[int] | None = None

    def __post_init__(self):
        self.dest_shape = (
            self.source_shape[0] - self.start_index,
            *self.source_shape[1:],
        )
        if (
            self.stop_index < MAX_FRAMES_PER_DATASET
            or self.stop_index < self.source_shape[0]
        ):
            self.dest_shape = (
                self.dest_shape[0] - (self.source_shape[0] - self.stop_index),
                *self.source_shape[1:],
            )

    def __add__(self, x):
        """Returns a dataset that has the same start index and shape as if the two were appended to each other."""
        return Dataset(
            "",
            source_shape=(
                self.source_shape[0] + x.source_shape[0],
                *self.source_shape[1:],
            ),
            start_index=self.start_index + x.start_index,
            stop_index=self.stop_index + x.stop_index,
        )


def split_datasets(
    dsets: list[str],
    data_shape: tuple[int, int, int],
    start_idx: int = 0,
    vds_shape: tuple[int, int, int] = None,
) -> list[Dataset]:
    """
    Splits the full data shape and start index up into values per dataset,
    given that each dataset has a maximum size.

    Args:
        dsets (Dataset): The input datasets.
        data_shape (tuple[int, int, int]): Shape of the data, usually defined as (num_frames, *image_size).
        start_idx (int, optional): The start point for the source data. Defaults to 0.
        vds_shape(tuple, optional): Desired shape of the VDS, usually defined as (num_frames, *image_size). \
            The number of frames must be smaller or equal to the one in full_data_shape. Defaults to None.

    Raises:
        ValueError: If the passed start index value is higher than the dataset lenght.
        ValueError: It the passed start index value is negative.

    Returns:
        list[Dataset]: A list of datasets.
    """
    if start_idx > data_shape[0]:
        raise ValueError(
            f"Start index {start_idx} must be less than full dataset length {data_shape[0]}"
        )
    if start_idx < 0:
        raise ValueError("Start index must be positive")

    if not isinstance(data_shape[0], int):
        block_vds_logger.warning("Datashape not passed as int, will attempt to cast")

    if not isinstance(start_idx, int):
        block_vds_logger.warning(
            "VDS start index not passed as int, will attempt to cast"
        )

    if vds_shape and not isinstance(vds_shape[0], int):
        block_vds_logger.warning(
            "VDS start index not passed as int, will attempt to cast"
        )

    if vds_shape is None:
        block_vds_logger.debug(
            "VDS shape not chosen, it will be calculated from the full data shape and the chosen start index."
        )
        vds_shape = (data_shape[0] - start_idx, *data_shape[1:])

    full_frames = int(data_shape[0])
    end_cut_frames = int(full_frames - vds_shape[0]) - int(start_idx)

    result = []
    for dset_name in dsets:
        dset = Dataset(
            name=dset_name,
            source_shape=(min(MAX_FRAMES_PER_DATASET, full_frames), *data_shape[1:]),
            start_index=min(MAX_FRAMES_PER_DATASET, max(int(start_idx), 0)),
            stop_index=min(MAX_FRAMES_PER_DATASET, (full_frames - end_cut_frames)),
        )
        # if start index == 1000 then that source dataset is not used and we should
        # not pass it on to use as a source for the VDS
        # Same goes if all datasets from last files are not used
        if dset.start_index != MAX_FRAMES_PER_DATASET:
            if dset.stop_index > 0 and dset.stop_index <= MAX_FRAMES_PER_DATASET:
                result.append(dset)
        start_idx -= MAX_FRAMES_PER_DATASET
        full_frames -= MAX_FRAMES_PER_DATASET

    return result


def create_virtual_layout(datasets: list[Dataset], data_type: DTypeLike):
    """
    Create a virtual layout and populate it based on the provided data.

    Args:
        datasets (list[Dataset]): A list of datasets that are to be merged.
        data_type (DTypeLike): The type of the input data.

    Returns:
        layout (h5py.VirtualLayout): Virtual layout.
    """
    full_dataset: Dataset = reduce(operator.add, datasets)
    layout = h5py.VirtualLayout(shape=full_dataset.dest_shape, dtype=data_type)

    dest_start = 0
    for dataset in datasets:
        if dataset.stop_index == dataset.source_shape[0]:
            dest_end = dest_start + dataset.source_shape[0] - dataset.start_index
        else:
            dest_end = dest_start + dataset.dest_shape[0]

        vsource = h5py.VirtualSource(
            ".", "/entry/data/" + dataset.name, shape=dataset.source_shape
        )

        layout[dest_start:dest_end, :, :] = vsource[
            dataset.start_index : dataset.stop_index, :, :
        ]
        dest_start = dest_end

    return layout


def image_vds_writer(
    nxsfile: h5py.File,
    full_data_shape: tuple | list,
    start_index: int = 0,
    vds_shape: tuple | list | None = None,
    data_type: DTypeLike = np.uint16,
    entry_key: str = "data",
):
    """
    Virtual DataSet writer function for image data.

    Args:
        nxsfile (h5py.File): Handle to NeXus file being written.
        full_data_shape (tuple | list): Shape of the full dataset, usually defined as (num_frames, *image_size).
        start_index(int): The start point for the source data. Defaults to 0.
        vds_shape(tuple, optional): Desired shape of the VDS, usually defined as (num_frames, *image_size). \
            The number of frames must be smaller or equal to the one in full_data_shape. Defaults to None.
        data_type (DTypeLike, optional): The type of the input data. Defaults to np.uint16.
        entry_key (str, optional): Entry key for the Virtual DataSet name. Defaults to data.
    """
    block_vds_logger.debug("Start creating VDS ...")
    # Where the vds will go
    nxdata = nxsfile["/entry/data"]
    dset_names = find_datasets_in_file(nxdata)

    vds_shape = (
        tuple(vds_shape)
        if vds_shape is not None
        else (full_data_shape[0] - start_index, *full_data_shape[1:])
    )

    # Hack for datasets with no maximum number of frames (eg. Singla)
    if len(dset_names) == 1 and full_data_shape[0] > MAX_FRAMES_PER_DATASET:
        # nxdata[dset_names[0]].shape[0] > MAX_FRAMES_PER_DATASET
        # .maxshape[0] is None
        datasets = [
            Dataset(
                name=dset_names[0],
                source_shape=full_data_shape,
                start_index=start_index,
                stop_index=full_data_shape[0],
            )
        ]
    else:
        datasets = split_datasets(dset_names, full_data_shape, start_index, vds_shape)

    layout = create_virtual_layout(datasets, data_type)

    # Writea Virtual Dataset in NeXus file
    nxdata.create_virtual_dataset(entry_key, layout, fillvalue=-1)
    block_vds_logger.debug("VDS correctly written to NeXus file.")
