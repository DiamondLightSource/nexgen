"""
General tools for blank data writing.
"""

import h5py

import numpy as np

from pathlib import Path
from hdf5plugin import Bitshuffle
from typing import List, Tuple, Union

# Eiger specific
eiger_modules = {"1M": (1, 2), "4M": (2, 4), "9M": (3, 6), "16M": (4, 8)}
eiger_mod_size = (512, 1028)
eiger_gap_size = (38, 12)
intra_mod_gap = 2

# Tristan specific
tristan_modules = {"10M": (2, 5)}
tristan_mod_size = (515, 2069)  # (H, V)
tristan_gap_size = (117, 45)  # TODO Calculated value. Double check.


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


def build_a_tristan(image_size: Union[List, Tuple]) -> np.ndarray:
    """
    Generate a Tristan-like blank image.

    Args:
        image_size (Union[List, Tuple]): Defines image dimensions as (slow_axis , fast_axis).

    Returns:
        np.ndarray: Array of zeros with a Tristan-like mask.
    """
    # FIXME This is hardcoded for a Tristan 10M.
    n_modules = tristan_modules["10M"]

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
        img = build_a_tristan(image_size)
    else:
        # Do nothing for now, just add zeros
        img = np.zeros(image_size, dtype=np.uint16)

    # Determine single dataset shape: (num, *img_size), where max(num)=1000.
    # Really dumb version ...
    if tot_num_images <= 1000:
        dset_shape = [1000]
    elif tot_num_images % 1000 == 0:
        dset_shape = (tot_num_images // 1000) * [1000]
    else:
        dset_shape = (tot_num_images // 1000) * [1000] + [tot_num_images % 1000]

    # Just a quick check
    assert len(dset_shape) == len(datafiles), "Number of files desn't match shape."

    # Start writing file
    for filename, sh0 in zip(datafiles, dset_shape):
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


def generate_event_files():
    pass
