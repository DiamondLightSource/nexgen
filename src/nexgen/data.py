"""
General utilities for data writing.
"""

import h5py
import numpy as np
from hdf5plugin import Bitshuffle


def find_filename_template():
    """
    Use the master file name as a template to get the data file names.

    Args:
    Returns:
    """
    pass


def generate_image_data(filename, shape, write_mode="x"):
    """
    Generate a HDF5 file with blank images.

    Args:
        filename:   Name of the output data file to be written.
        shape:      Tuple defining dataset dimensions.
        write_mode: Mode for writing the output HDF5 file.  Accepts any valid
                    h5py file opening mode.
    """
    data = np.zeros(shape[1:], dtype="i4")
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
            start_dset = dset[i, :, :]
            dset[i, :, :] = start_dset + data
    print(f"{shape[0]} images written.")


# This will need some rethinking in the future,
# for now it's just to make examples to show GDA.
def generate_event_data(filename, n_events, n_cues=100, write_mode="x"):
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
