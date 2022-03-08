"""
General tools for blank data writing.
"""

import h5py
import time
import logging

import numpy as np

from pathlib import Path
from hdf5plugin import Bitshuffle
from typing import List, Tuple, Union

data_logger = logging.getLogger("NeXusGenerator.writer.data")

# Random number generator
rng = np.random.default_rng()

# Eiger specific
eiger_modules = {"1M": (1, 2), "4M": (2, 4), "9M": (3, 6), "16M": (4, 8)}
eiger_mod_size = (512, 1028)
eiger_gap_size = (38, 12)
intra_mod_gap = 2

# Tristan specific
clock_freq = int(6.4e8)
tristan_modules = {"10M": (2, 5), "2M": (1, 2)}
tristan_mod_size = (515, 2069)  # (H, V)
tristan_gap_size = (117, 45)

# Pre-defined chunk size
tristan_chunk = 2097152


# Build-a-detector functions
def build_an_eiger(
    image_size: Union[List, Tuple],
    det_description: str,
    n_modules: Tuple[int, int] = None,
) -> np.ndarray:
    """
    Generate an Eiger-like blank image.

    Args:
        image_size (Union[List, Tuple]): Defines image dimensions as (slow_axis , fast_axis).
        det_description (str): Identifies the type of Eiger detector.
        n_modules (Tuple[int, int], optional): Number of modules in the detector. Defaults to None.

    Returns:
        IM (np.ndarray): Array of zeros with an Eiger-like mask.
    """
    for k, v in eiger_modules.items():
        if k in det_description.upper():
            n_modules = v

    IM = np.zeros(image_size, dtype=np.uint16)

    # Horizontal modules
    for i in range(1, n_modules[0] + 1):
        IM[
            :,
            i * eiger_mod_size[1]
            + (i - 1) * eiger_gap_size[1] : i * (eiger_mod_size[1] + eiger_gap_size[1]),
        ] = -1
    # Vertical modules
    for j in range(1, n_modules[1] + 1):
        IM[
            j * eiger_mod_size[0]
            + (j - 1) * eiger_gap_size[0] : j * (eiger_mod_size[0] + eiger_gap_size[0]),
            :,
        ] = -1

    # Intra module gap
    mid = []
    for n in range(n_modules[0]):
        mid.append(
            int(eiger_mod_size[1] / 2) + n * (eiger_mod_size[1] + eiger_gap_size[1])
        )
    for m in mid:
        IM[:, (m - 1) : (m + 1)] = -1

    return IM


def build_a_tristan(
    image_size: Union[List, Tuple],
    det_description: str,
) -> np.ndarray:
    """
    Generate a Tristan-like blank image.

    Args:
        image_size (Union[List, Tuple]): Defines image dimensions as (slow_axis , fast_axis).
        det_description (str): Identifies the type of Eiger detector.

    Returns:
        np.ndarray: Array of zeros with a Tristan-like mask.
    """
    for k, v in tristan_modules.items():
        if k in det_description.upper():
            n_modules = v

    IM = np.zeros(image_size, dtype=np.uint16)

    # Horizontal modules
    for i in range(1, n_modules[0] + 1):
        IM[
            :,
            i * tristan_mod_size[1]
            + (i - 1)
            * tristan_gap_size[1] : i
            * (tristan_mod_size[1] + tristan_gap_size[1]),
        ] = -1
    # Vertical modules
    for j in range(1, n_modules[1] + 1):
        IM[
            j * tristan_mod_size[0]
            + (j - 1)
            * tristan_gap_size[0] : j
            * (tristan_mod_size[0] + tristan_gap_size[0]),
            :,
        ] = -1

    return IM


def generate_image_files(
    datafiles: List[Union[Path, str]],
    image_size: Union[List, Tuple],
    det_description: str,
    tot_num_images: int,
):
    """
    Generate HDF5 files of blank images.

    Args:
        datafiles (List[Union[Path, str]]): List of HDF5 files to be written.
        image_size (Union[List, Tuple]): Image dimensions as (slow_axis, fast_axis).
        det_description (str): Type of detector. The string should include the number of modules.
        tot_num_images (int): Total number of images to be written across the files.
    """
    # Write some blank data in the shape of a detector
    if "eiger" in det_description.lower():
        img = build_an_eiger(image_size, det_description)
    elif "tristan" in det_description.lower():
        img = build_a_tristan(image_size, det_description)
    else:
        # Do nothing for now, just add zeros
        img = np.zeros(image_size, dtype=np.uint16)

    # Determine single dataset shape: (num, *img_size), where max(num)=1000.
    dset_shape = (tot_num_images // 1000) * [1000] + [tot_num_images % 1000]
    # if tot_num_images <= 1000:
    #    dset_shape = [tot_num_images]
    # elif tot_num_images % 1000 == 0:
    #    dset_shape = (tot_num_images // 1000) * [1000]
    # else:
    #    dset_shape = (tot_num_images // 1000) * [1000] + [tot_num_images % 1000]

    # Just a quick check
    assert len(dset_shape) == len(datafiles), "Number of files desn't match shape."

    # Start writing files
    for filename, sh0 in zip(datafiles, dset_shape):
        data_logger.info(f"Writing {filename} ...")
        tic = time.process_time()
        with h5py.File(filename, "w") as fh:
            dset = fh.create_dataset(
                "data",
                shape=(sh0, *image_size),
                dtype=np.uint16,
                chunks=(1, *image_size),
                **Bitshuffle(),
            )
            # Use direct chunk write
            dset[0, :, :] = img
            f, ch = dset.id.read_direct_chunk((0, 0, 0))
            for j in range(1, sh0):
                dset.id.write_direct_chunk((j, 0, 0), ch, f)
        toc = time.process_time()
        data_logger.info(f"Writing {sh0} images took {toc - tic:.2f} s.")


# Event list generator
# TODO Better than before, but this is still pretty slow.
def pseudo_event_list(
    x_lim: Tuple[int, Union[int, None]],
    y_lim: Tuple[int, Union[int, None]],
    exp_time: float,
) -> Tuple[List, List]:
    """
    Generate a pseudo-events list with positions and timestamps.

    Args:
        x_lim (Tuple[int, Union[int, None]]): Minimum and maximum position along the fast axis.
        y_lim (Tuple[int, Union[int, None]]): Minimum and maximum position along the slow axis.
        exp_time (float): Total exposure time, in seconds.

    Returns:
        pos_list, time_list (Tuple[List, List]): Lists of pseudo-event positions and relative timestamps.
    """
    pos_list = []
    time_list = []

    for _ in range(tristan_chunk):
        dist = rng.uniform(0, 1)
        x = (
            np.random.randint(x_lim[0], x_lim[1])
            if len(x_lim) > 1
            else np.random.randint(x_lim[0])
        )
        y = (
            np.random.randint(y_lim[0], y_lim[1])
            if len(y_lim) > 1
            else np.random.randint(y_lim[0])
        )
        loc = np.uint32(x * np.uint32(0x2000) + y)
        pos_list.append(loc)
        t = np.uint64((exp_time + dist) * clock_freq)
        time_list.append(t)

    return pos_list, time_list


def generate_event_files(
    datafiles: List[Union[Path, str]],
    num_chunks: int,
    det_description: str,
    exp_time: float,
):
    """
    Generate HDF5 files of pseudo events.

    Args:
        datafiles (List[Union[Path, str]]): List of HDF5 files to be written.
        num_chunks (int): Chunks of events to be written per file.
        det_description (str): Type of detector. The string should include the number of modules.
        exp_time (float): Total exposure time, in seconds.
    """
    # A bunch of things to be done here first ...
    # Get number of modules in the Tristan detector
    for k, v in tristan_modules.items():
        if k in det_description.upper():
            n_modules = v

    # Some blank cues
    blank_cues = np.zeros(tristan_chunk, dtype=np.uint16)

    # TODO FIXME speed this up!
    data_logger.info(
        f"Start generating one chunk of pseudo events for {n_modules} modules of {det_description}"
    )
    t0 = time.process_time()
    EV_dict = {}
    for i in range(n_modules[0]):
        for j in range(n_modules[1]):
            I = (
                i * (tristan_mod_size[1] + tristan_gap_size[1]),
                (i + 1) * tristan_mod_size[1] + i * tristan_gap_size[1],
            )
            J = (
                j * (tristan_mod_size[0] + tristan_gap_size[0]),
                (j + 1) * tristan_mod_size[0] + j * tristan_gap_size[0],
            )
            EV_dict[(i, j)] = pseudo_event_list(I, J, exp_time)
    t1 = time.process_time()
    data_logger.info(f"Time taken to generate pseudo-event list: {t1-t0:.2f} s.")

    # Find total number of events to be written to file
    num_events = tristan_chunk * num_chunks

    # Start writing files
    for filename, K in zip(datafiles, EV_dict.keys()):
        data_logger.info(f"Writing {filename} ...")
        tic = time.process_time()
        with h5py.File(filename, "w") as fh:
            fh.create_dataset("cue_id", data=blank_cues, **Bitshuffle())
            fh.create_dataset("cue_timestamp_zero", data=blank_cues, **Bitshuffle())
            ev_id = fh.create_dataset(
                "event_id",
                shape=(num_events,),
                dtype=np.uint32,
                chunks=(tristan_chunk,),
                **Bitshuffle(),
            )
            ev_t = fh.create_dataset(
                "event_timestamp_zero",
                shape=(num_events,),
                dtype=np.uint64,
                chunks=(tristan_chunk,),
                **Bitshuffle(),
            )
            ev_en = fh.create_dataset(
                "event_energy",
                shape=(num_events,),
                dtype=np.uint32,
                chunks=(tristan_chunk,),
                **Bitshuffle(),
            )

            # Use direct chunk write
            ev_id[:tristan_chunk] = EV_dict[K][0]
            ev_t[:tristan_chunk] = EV_dict[K][1]
            ev_en[:tristan_chunk] = blank_cues
            f_id, ch_id = ev_id.id.read_direct_chunk((0,))
            f_t, ch_t = ev_t.id.read_direct_chunk((0,))
            f_en, ch_en = ev_en.id.read_direct_chunk((0,))
            for h in range(1, num_chunks):
                ev_id.id.write_direct_chunk((h * tristan_chunk,), ch_id, f_id)
                ev_t.id.write_direct_chunk((h * tristan_chunk,), ch_t, f_t)
                ev_en.id.write_direct_chunk((h * tristan_chunk,), ch_en, f_en)
        toc = time.process_time()
        data_logger.info(f"Writing {num_events} events took {toc - tic:.2f} s.")
