"""
Utilities for writing new NeXus format files.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import h5py  # isort: skip
import numpy as np
from hdf5plugin import Bitshuffle, Blosc
from numpy.typing import ArrayLike

from ..nxs_utils import Axis

# Logger
NXclassUtils_logger = logging.getLogger("nexgen.NXclass_writers.utils")
NXclassUtils_logger.setLevel(logging.DEBUG)

# Define Timestamp dataset names
TSdset = Literal["start_time", "end_time", "end_time_estimated"]


def create_attributes(nxs_obj: h5py.Group | h5py.Dataset, names: tuple, values: tuple):
    """
    Create or overwrite attributes with additional metadata information.

    If any of the values are strings, these will first be converted into fixed-width \
    bytesrings.

    Args:
        nxs_obj (h5py.Group | h5py.Dataset): NeXus object to which the \
            attributes should be attached.
        names (tuple): The names of the new attributes.
        values (tuple): The attribute values asociated to the names.
    """
    for n, v in zip(names, values):
        if isinstance(v, str):
            # If a string, convert to a numpy bytestring
            v = np.bytes_(v)
        h5py.AttributeManager.create(nxs_obj, name=n, data=v)


def set_dependency(dep_info: str, path: str = None) -> np.bytes_:
    """
    Define value for "depends_on" attribute.
    If the attribute points to the head of the dependency chain, simply pass \
        "." for dep_info.

    Args:
        dep_info (str): The name of the transformation upon which the current \
            one depends on.
        path (str): Where the transformation is. Set to None, if passed it \
            points to location in the NeXus tree.
    Returns:
        The value to be passed to the attribute "depends_on" as a fixed-width \
            bytestring.
    """
    if dep_info == ".":
        return np.bytes_(".")
    if path:
        if path.endswith("/") is False:
            path += "/"
        return np.bytes_(path + dep_info)
    else:
        return np.bytes_(dep_info)


def calculate_origin(
    beam_center_fs: list | tuple,
    fs_pixel_size: list | tuple,
    fast_axis_vector: tuple,
    slow_axis_vector: tuple,
    mode: str = "1",
) -> tuple[list, float]:
    """
    Calculate the offset of the detector.

    This function returns the detector origin array, which is saved as the \
        vector attribute of the module_offset field.
    The value to set the module_offset to is also returned: the magnitude of \
        the displacement if the vector is normalized, 1.0 otherwise
    Assumes that fast and slow axis vectors have already been converted to \
        mcstas if needed.

    Args:
        beam_center_fs (list | tuple): Beam center position in fast and slow direction.
        fs_pixel_size (list | tuple): Pixel size in fast and slow direction, in m.
        fast_axis_vector (tuple): Fast axis vector.
        slow_axis_vector (tuple): Slow axis vector.
        mode (str, optional): Decide how origin should be calculated.
            If set to "1" the displacement vector is un-normalized \
                and the offset value set to 1.0.
            If set to "2" the displacement is normalized and the \
                offset value is set to the magnitude of the displacement.
            Defaults to "1".

    Returns:
        det_origin (list): Displacement of beam center, vector attribute of module_offset.
        offset_val (float): Value to assign to module_offset, depending whether \
            det_origin is normalized or not.
    """
    # what was calculate module_offset
    x_scaled = beam_center_fs[0] * fs_pixel_size[0]
    y_scaled = beam_center_fs[1] * fs_pixel_size[1]
    # Detector origin
    det_origin = x_scaled * np.array(fast_axis_vector) + y_scaled * np.array(
        slow_axis_vector
    )
    det_origin = list(-det_origin)
    if mode == "1":
        offset_val = 1.0
    else:
        offset_val = math.hypot(*det_origin[:-1])
    return det_origin, offset_val


def find_number_of_images(datafile_list: list[Path], entry_key: str = "data") -> int:
    """
    Calculate total number of images when there's more than one input HDF5 file.

    Args:
        datafile_list (list[Path]): List of paths to the input image files.
        entry_key (str):    Key for the location of the images inside the \
            data files. Defaults to "data".

    Returns:
        num_images (int): Total number of images.
    """
    num_images = 0
    for filename in datafile_list:
        with h5py.File(filename, "r") as f:
            num_images += f[entry_key].shape[0]
    return int(num_images)


def calculate_estimated_end_time(
    start_time: datetime | str, tot_collection_time: float
) -> str:
    time_format = r"%Y-%m-%dT%H:%M:%SZ"

    if isinstance(start_time, str):
        start_time = start_time.format("%Y-%m-%dT%H:%M:%S")
        start_time = datetime.strptime(start_time.strip("Z"), time_format.strip("Z"))

    est_end = start_time + timedelta(seconds=tot_collection_time)
    return est_end.strftime(time_format)


def mask_and_flatfield_writer(
    nxdet_grp: h5py.Group,
    dset_name: str,
    dset_data: str | ArrayLike,
    applied_val: bool,
):
    """ Utility function to write mask or flatfield to NXdetector group for \
        image data when not already linked to the _meta.h5 file.
    If the pixel_mask/flatfield data is passed as a string, it will be assumed \
        to be a file path and the writer will try to set up an external link to it.

    Args:
        nxdet_grp (h5py.Group): Handle to HDF5 NXdetector group.
        dset_name (str): Name of the new field/dataset to be written.
        dset_data (str | ArrayLike): Dataset data to be written in the field. \
            Can be a string or an array-like dataset. \
            If the data type is a numpy ndarray, it will be compressed before writing.
        applied_val (bool): Value to write to `{flatfield,pixel_mask}_applied` fields.
    """
    if dset_data is None:
        NXclassUtils_logger.warning(
            f"""
            No copy of the {dset_name} has been found, either as a file or dataset.
            Fields {dset_name} and {dset_name}_applied will not be written to file.
            """
        )
        return
    nxdet_grp.create_dataset(
        f"{dset_name}_applied",
        data=applied_val,
    )
    NXclassUtils_logger.debug(f"{dset_name}_applied set to: {applied_val}.")
    if isinstance(dset_data, str):
        try:
            link_path = Path(dset_data)
            NXclassUtils_logger.debug(
                f"Setting external link for {dset_name} to {link_path}."
            )
            nxdet_grp[dset_name] = h5py.ExternalLink(link_path.name, "/")
        except Exception as e:
            NXclassUtils_logger.error(
                f"Impossible to write external link to {dset_data} for {dset_name}."
                "Field {dset_name} not written."
            )
            NXclassUtils_logger.error(f"{e}", exc_info=1)
    elif isinstance(dset_data, np.ndarray):
        NXclassUtils_logger.debug(f"Writing a compressed copy of array in {dset_name}.")
        write_compressed_copy(nxdet_grp, dset_name, data=dset_data)
    else:
        NXclassUtils_logger.debug(
            f"{dset_name} of type {type(dset_data)}, writing as is."
        )
        nxdet_grp.create_dataset(dset_name, data=dset_data)
    return


def mask_and_flatfield_writer_for_event_data(
    nxdet_grp: h5py.Group,
    dset_name: str,
    dset_data_file: str,
    applied_val: bool,
    wdir: Path,
    detector_name: str = "tristan",
):
    if dset_data_file is None:
        NXclassUtils_logger.warning(
            f"No {dset_name} data file passed; {dset_name} won't be written."
        )
        return

    nxdet_grp.create_dataset(f"{dset_name}_applied", data=applied_val)
    NXclassUtils_logger.debug(
        f"Looking for file {dset_data_file} in {wdir.as_posix()}."
    )
    filename = [
        wdir / dset_data_file for f in wdir.iterdir() if dset_data_file == f.name
    ]
    if filename:
        NXclassUtils_logger.debug(f"File {dset_name} found in working directory.")
        write_compressed_copy(
            nxdet_grp,
            dset_name,
            filename=filename[0],
            filter_choice="blosc",
            dset_key="image",
        )
    else:
        NXclassUtils_logger.warning(
            f"No {dset_name} file found in working directory."
            "Writing an ExternalLink."
        )
        file_loc = Path(dset_data_file)
        image_key = "image" if "tristan" in detector_name.lower() else "/"
        nxdet_grp[dset_name] = h5py.ExternalLink(file_loc.name, image_key)
    return


# Copy and compress a dataset inside a specified NXclass
def write_compressed_copy(
    nxgroup: h5py.Group,
    dset_name: str,
    data: ArrayLike = None,
    filename: Path | str = None,
    filter_choice: str = "bitshuffle",
    dset_key: str = "image",
    **kwargs,
):
    """
    Write a compressed copy of some dataset in the desired HDF5 group, using \
        the filter of choice with lz4 compression. Available filters at this \
        time include "Blosc" and "Bitshuffle" (default).
    The main application for this function in nexgen is to write a compressed \
        copy of a pixel mask or a flatfield file/dataset directly into the \
        NXdetector group of a NXmx NeXus file.
    The data and filename arguments are mutually exclusive as only one of them \
        can be used as input.
    If a filename is passed, it is also required to pass the key for the \
        relevant dataset to be copied. Failure to do so will result in nothing being \
        written to the NeXus file.

    Args:
        nxgroup (h5py.Group): Handle to HDF5 group.
        dset_name (str): Name of the new dataset to be written.
        data (ArrayLike, optional): Dataset to be compressed. Defaults to None.
        filename (Path | str, optional): Filename containing the dataset to be \
            compressed into the NeXus file. Defaults to None.
        filter_choice (str, optional): Filter to be used for compression. \
            Either blosc or bitshuffle. Defaults to bitshuffle.
        dset_key (str, optional): Dataset name inside the passed file. \
            Defaults to "image".

    Keyword Args:
        block_size (int, optional): Number of elements per block, it needs to \
            be divisible by 8. Needed for Bitshuffle filter. Defaults to 0.

    Raises:
        ValueError: If both a dataset and a filename have been passed to the function.
    """
    if data is not None and filename is not None:
        raise ValueError(
            "The dset and filename arguments are mutually exclusive."
            "Please pass only the one from which the data should be copied."
        )

    if filename and not dset_key:
        NXclassUtils_logger.warning(
            f"Missing key to find the dataset to be copied inside {filename}. {dset_name} will not be written into the NeXus file."
        )
        return

    if filename:
        with h5py.File(filename, "r") as fh:
            data = fh[dset_key][()]

    if filter_choice.lower() == "blosc":
        nxgroup.create_dataset(
            dset_name, data=data, **Blosc(cname="lz4", shuffle=Blosc.BITSHUFFLE)
        )
    elif filter_choice.lower() == "bitshuffle":
        block_size = (
            0 if "block_size" not in list(kwargs.keys()) else kwargs["block_size"]
        )
        nxgroup.create_dataset(
            dset_name, data=data, **Bitshuffle(nelems=block_size, cname="lz4")
        )
    else:
        NXclassUtils_logger.warning(
            "Unknown filter choice, no dataset will be written."
        )
        return
    NXclassUtils_logger.info(
        f"A compressed copy of the {dset_name} has been written into the NeXus file."
    )


def add_sample_axis_groups(nxsample: h5py.Group, axis_list: list[Axis]):
    """
    Add non-standard "sample_{phi,omega,...}" groups to NXsample. These may be needed for \
    some autoprocessing tools to work correctly.

    Args:
        nxsample (h5py.Group): NeXus NXsample group.
        axis_list (list[Axis]): List of goniometer axes.
    """
    NXclassUtils_logger.debug("Add non-standard fields for autoPROC to work.")
    nxtransf = nxsample["transformations"]
    for ax in axis_list:
        grp_name = f"sample_{ax.name[-1]}" if "sam" in ax.name else f"sample_{ax.name}"
        nx_ax = nxsample.require_group(grp_name)
        # NOTE: NX_class here set to NXtransformations instead of NXpositioner
        # One step closer to standard.  TO BE TESTED
        create_attributes(nx_ax, ("NX_class",), ("NXtransformations",))
        nx_ax[ax.name] = nxtransf[ax.name]
        if f"{ax.name}_end" in nxtransf.keys():
            nx_ax[f"{ax.name}_end"] = nxtransf[f"{ax.name}_end"]
        if f"{ax.name}_increment_set" in nxtransf.keys():
            nx_ax[f"{ax.name}_increment_set"] = nxtransf[f"{ax.name}_increment_set"]
