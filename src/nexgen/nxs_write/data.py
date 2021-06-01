"""
General tools for data writing.
"""

import sys
import h5py
import numpy as np
from pathlib import Path
from hdf5plugin import Bitshuffle


def get_filename_template(master_filename: Path) -> str:
    """
    Get the data file name template from the master file.

    Args:
        master_filename:    Path object containing the name of master file.
                            The format should be either file_master.h5 or file.nxs.
    Returns:
        filename_template:  String template for the name of blank data file.
    """
    if master_filename.suffix == ".nxs":
        filename_root = master_filename.stem
        filename_template = master_filename.parent / f"{filename_root}_%0{6}d.h5"
    elif master_filename.suffix == ".h5":
        filename = master_filename.stem.replace("master", f"%0{6}d")
        filename_template = master_filename.parent / f"{filename}.h5"
    else:
        sys.exit("Master file did not have the expected format.")
    # so that filename_template.as_posix() % 1 will become filename_000001.h5
    return filename_template.as_posix()


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


def write_vds():
    pass


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
