"""Create a Virtual DataSet with a strided mapping, ie mappaing every {n} frames from each file"""

import logging
from typing import Sequence

import h5py
import numpy as np
from numpy.typing import DTypeLike
from pydantic.dataclasses import dataclass

from nexgen.tools.vds_tools.utils import find_datasets_in_file

stride_vds_logger = logging.getLogger("nexgen.tools.vds_tools.strided_mapping")


@dataclass
class SingleDataset:
    name: str
    # Full size of the source dataset
    src_shape = Sequence[int]
    # Index to start the mapping from, usually 0 or 1 for this
    start_index: int = 0
    # Step for slicing the dataset. Defaults to every other image
    stride: int = 2


def create_dataset_list(
    nxdata: h5py.Group, start_index: int, stride: int = 2
) -> list[SingleDataset]:
    # NOTE. For now just keeping the assumption of always starting from 0
    # TO BE ADDED LATER
    dset_names = find_datasets_in_file(nxdata)

    datasets = []
    for name in dset_names:
        dset = SingleDataset(
            name=name,
            src_shape=nxdata[name].shape,
            start_index=start_index,
            stride=stride,
        )
        datasets.append(dset)

    if len(datasets) == 0:
        msg = "No datasets found in NXdata to create VDS."
        stride_vds_logger.error(msg)
        raise ValueError(msg)

    return datasets


def create_vds_layout(
    datasets: list[SingleDataset], dest_shape: Sequence[int], data_type: DTypeLike
) -> h5py.VirtualLayout:
    stride_vds_logger.debug(f"""Creating VDS layout with shape {dest_shape},
        start_index {datasets[0].start_index} and stride {datasets[0].stride}""")
    layout = h5py.VirtualLayout(shape=dest_shape, dtype=data_type)

    num_dsets = len(datasets)
    dest_start = 0
    for dataset in datasets:
        dest_end = int(dest_shape[0] / num_dsets) + dest_start
        vsource = h5py.VirtualSource(
            ".", f"/entry/data/{dataset.name}", shape=dataset.src_shape
        )
        layout[dest_start:dest_end, :, :] = vsource[
            dataset.start_index : dataset.src_shape[0] : dataset.stride, :, :
        ]
        dest_start = dest_end

    return layout


def write_strided_vds(
    nxsfile: h5py.File,
    full_data_shape: Sequence[int],
    start_index: int,
    stride: int = 2,
    data_type: DTypeLike = np.uint32,
    vds_key: str = "data",
):
    nxdata = nxsfile["/entry/data"]
    datasets = create_dataset_list(nxdata, start_index, stride)

    vds_shape = (full_data_shape[0] // stride, *full_data_shape[1:])
    stride_vds_logger.info(f"VDS in {nxsfile} will have shape {vds_shape}")

    layout = create_vds_layout(datasets, vds_shape, data_type)
    stride_vds_logger.debug("Layout created")

    # Write VDS in nxs file
    nxdata.create_virtual_dataset(vds_key, layout, fillvalue=-1)
    stride_vds_logger.info(f"VDS written to {nxsfile}")
