"""
General tools for data writing.
"""

import h5py
import logging

import numpy as np

from pathlib import Path
from hdf5plugin import Bitshuffle
from typing import List, Tuple, Optional, Union

data_logger = logging.getLogger("NeXusGenerator.write.data")

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
    # TODO FIXME if multiple files split number of images across them.
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


def vds_writer(nxsfile: h5py.File, datafiles: List[Path], vds_writer: str):
    """
    Write a Virtual Dataset file for image data.

    Args:
        nxsfile:    NeXus file being written.
        datafiles:  List of paths to source files.
        vds_writer: Choose whether to write a virtual dataset under /entry/data/data in the NeXus file
                    or a _vds.h5 file added to the NeXus file as an External Link.
    """
    data_logger.info("Start creating VDS ...")
    entry_key = "data"
    # Calculate total number of frames across the files
    frames = [h5py.File(f, "r")[entry_key].shape[0] for f in datafiles]
    tot_frames = sum(frames)
    # Get shape of the detector
    sh = h5py.File(datafiles[0], "r")[entry_key].shape[1:]

    dtyp = h5py.File(datafiles[0], "r")[entry_key].dtype

    # Create virtual layout
    layout = h5py.VirtualLayout(shape=(tot_frames,) + sh, dtype=dtyp)
    start = 0
    for n, filename in enumerate(datafiles):
        end = start + frames[n]
        vsource = h5py.VirtualSource(
            filename.name, entry_key, shape=(frames[n],) + sh
        )  # Source definition
        layout[start:end:1, :, :] = vsource
        start = end

    if vds_writer == "dataset":
        # Write virtual dataset in nexus file
        nxdata = nxsfile["entry/data"]
        nxdata.create_virtual_dataset(entry_key, layout, fillvalue=-1)
        data_logger.info("VDS written to NeXus file.")
    elif vds_writer == "file":
        # Create a _vds.h5 file and add link to nexus file
        s = Path(nxsfile.filename).expanduser().resolve()
        vds_filename = s.parent / f"{s.stem}_vds.h5"
        del s
        with h5py.File(vds_filename, "w") as vds:
            vds.create_virtual_dataset("data", layout, fillvalue=-1)
        nxsfile["entry/data/data"] = h5py.ExternalLink(vds_filename.name, "data")
        data_logger.info(f"{vds_filename} written and link added to NeXus file.")
