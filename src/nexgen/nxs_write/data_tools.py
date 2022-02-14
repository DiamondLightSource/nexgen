"""
General tools for data writing.
"""

import h5py
import logging

import numpy as np

from pathlib import Path
from hdf5plugin import Bitshuffle
from typing import List, Tuple, Optional, Union

data_logger = logging.getLogger("NeXusGenerator.writer.data")

# Writer functions
def data_writer(
    datafiles: List[Path],
    data_type: Tuple[str, int],
    image_size: Optional[Union[List, Tuple]] = None,
    scan_range: np.ndarray = None,
):
    """
    Write N images or events to n files.

    Args:
        datafiles:  List of Path objects pointing at data files to be written.
        data_type:  Tuple (str, int) identifying whether the files to be written contain images or events.
        image_size: Tuple or List defining image dimensions.
        scan_range: Numpy array containing the values of the rotation axis during the scan.
    """
    for filename in datafiles:
        data_logger.info(f"Writing {filename} ...")
        if data_type[0] == "images":
            dset_shape = (len(scan_range),) + tuple(image_size)
            generate_image_data(filename, dset_shape)
        else:
            generate_event_data(filename, data_type[1])


def generate_image_data(
    filename: Optional[Union[Path, str]],
    shape: Tuple[int, int, int],
    write_mode: str = "x",
):
    """
    Generate a HDF5 file with blank images.

    Args:
        filename:   Name of the output data file to be written.
        shape:      Tuple defining dataset dimensions as follows: (img_number, slow_axis, fast_axis).
        write_mode: Mode for writing the output HDF5 file.  Accepts any valid
                    h5py file opening mode.
    """
    data = np.zeros(shape[1:], dtype="i4")

    # GW comments in conversation 2022-01-18
    # thoughts -
    # we should have a real mask here which looks like a
    # mask from an Eiger e.g. with all the zero pixels in
    # the right places then _also_ we could really speed
    # this up by compressing the data into a chunk then
    # using direct chunk write. Finally - should probably
    # split the data sets into blocks of 1,000 (as a parameter)
    # images so we have something more authentic.

    with h5py.File(filename, write_mode) as datafile:
        dset = datafile.create_dataset(
            "data",
            shape=shape,
            dtype="i4",
            chunks=(1, shape[1], shape[2]),
            **Bitshuffle(),
        )
        # Actually write the data in
        for i in range(shape[0]):
            # start_dset = dset[i, :, :]
            # print(i)
            dset[i, :, :] = data
    print(f"{shape[0]} images written.")


# FIXME
# This will need some rethinking in the future, for now it's just to make examples to show GDA.
def generate_event_data(
    filename: Optional[Union[Path, str]],
    n_events: int,
    n_cues: int = 100,
    write_mode: str = "x",
):
    """
    Generate a HDF5 file showing the structure of an event-mode dataset.

    Args:
        filename:   Name of the output data file to be written.
        n_events:   Length of the "blank" event stream.
        n_cues:     Length of the "blank" cue messages.
        write_mode: Mode for writing the output HDF5 file.  Accepts any valid
                    h5py file opening mode.
    """
    cues = np.zeros(n_cues, dtype="u4")
    events = np.zeros(n_events, dtype="u8")
    with h5py.File(filename, write_mode) as datafile:
        datafile.create_dataset("cue_id", data=cues, **Bitshuffle())
        datafile.create_dataset("cue_timestamp_zero", data=cues, **Bitshuffle())
        datafile.create_dataset("event_id", data=events, dtype="i4", **Bitshuffle())
        datafile.create_dataset("event_time_offset", data=events, **Bitshuffle())
        datafile.create_dataset("event_energy", data=events, **Bitshuffle())
    print(f"Stream of {n_events} written.")
