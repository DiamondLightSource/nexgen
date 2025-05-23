""" Helper functions for the MRC to Nexus converter """

import logging
import os
import re
from math import sqrt
from pathlib import Path
from typing import Union

import h5py
import hdf5plugin
import mrcfile
import numpy as np


def cal_wavelength(V0: float) -> float:
    """
    Compute the relativistic electron wavelength from the electron
    acceleration voltage.

    Arguments
    ---------
    V0 : int or float
        Acceleration voltage for electrons in Volts.

    Returns
    -------
    wlen : float
        Electron wavelength in Angstroms.

    For an acceleration voltage of 200000 V, the electron energy
    is 200 keV (set by default if V0 is zero).
    """

    h = 6.626e-34  # Planck's constant [J*s]
    m = 9.109e-31  # Electron mass [kg]
    e = 1.6021766208e-19  # Electron charge [C]
    c = 3e8  # Speed of light  [m/s]

    # Default to wavelength at 200 keV if voltage set to zero
    if V0 == 0:
        V0 = 200000
    wlen = h / sqrt(2 * m * e * V0 * (1 + e * V0 / (2 * m * c * c))) * 1e10
    return wlen  # Electron wavelength in Angstroms


def get_metadata(mrc_image: Union[str, Path], verbatim: bool = True) -> dict:
    """
    Extract metadata dictionary from an MRC file.

    Arguments
    ---------
    mrc_image : Path or str
        MRC file path.

    Returns
    -------
    hd : dict
        A dictionary containing metadata from the MRC file.

    The function extracts data from the MRC header and extended header
    dictionaries.
    """
    hd = {}  # Header dictionary

    test_file = mrcfile.open(mrc_image, mode="r")
    hd["data_shape"] = test_file.data.shape
    hd["original_data_type"] = test_file.data.dtype

    with mrcfile.open(mrc_image, header_only=True) as mrc:
        h = mrc.header
        try:
            xh = mrc.indexed_extended_header
        except AttributeError:
            # For mrcfile versions older than 1.5.0
            xh = mrc.extended_header

        hd["nx"] = h["nx"]
        hd["ny"] = h["ny"]
        hd["nz"] = h["nz"]
        hd["mx"] = h["mx"]
        hd["my"] = h["my"]
        hd["mz"] = h["mz"]

        h_ext_type = h["exttyp"].item()
        is_FEI = h_ext_type.startswith(b"FEI")
        is_FEI2 = h_ext_type.startswith(b"FEI2")

        if not is_FEI:
            return hd

        hd["alphaTilt"] = xh["Alpha tilt"][0]
        hd["integrationTime"] = xh["Integration time"][0]
        hd["tilt_axis"] = xh["Tilt axis angle"][0]
        hd["pixelSpacing"] = xh["Pixel size X"][0]

        if hd["pixelSpacing"] == 0:
            raise ValueError("Incorrect extended header")

        hd["acceleratingVoltage"] = xh["HT"][0]
        hd["camera"] = xh["Camera name"][0]
        hd["binning"] = xh["Binning Width"][0]
        hd["noiseReduction"] = xh["Ceta noise reduction"][0]
        hd["physicalPixel"] = 14e-6
        hd["wavelength"] = cal_wavelength(hd["acceleratingVoltage"])
        hd["cameraLength"] = (
            (hd["physicalPixel"] * hd["binning"])
            / (hd["pixelSpacing"] * hd["wavelength"] * 1e-10)
            * 1000.0
        )
        if not is_FEI2:
            return hd

        hd["scanRotation"] = xh["Scan rotation"][0]
        var = "diffractionPatternRotation"
        hd[var] = xh["Diffraction pattern rotation"][0]
        hd["imageRotation"] = xh["Image rotation"][0]
        hd["scanModeEnum"] = xh["Scan mode enumeration"][0]
        hd["acquisitionTimeStamp"] = xh["Acquisition time stamp"][0]
        hd["detectorCommercialName"] = xh["Detector commercial name"][0]
        hd["startTiltAngle"] = xh["Start tilt angle"][0]
        hd["endTiltAngle"] = xh["End tilt angle"][0]
        hd["tiltPerImage"] = xh["Tilt per image"][0]
        hd["tiltSpeed"] = xh["Tilt speed"][0]
        hd["beamCentreXpx"] = xh["Beam center X pixel"][0]
        hd["beamCentreYpx"] = xh["Beam center Y pixel"][0]
        hd["cfegFlashTimestamp"] = xh["CFEG flash timestamp"][0]
        hd["phasePlatePositionIndex"] = xh["Phase plate position index"][0]
        hd["objectiveApertureName"] = xh["Objective aperture name"][0]

        # Check if binning is correct
        assert hd["binning"] == 4096 / hd["nx"]

        return hd


def to_hdf5_data_file(
    files: list[Union[str, Path]], logger: logging.Logger, dtype: str = None
) -> tuple[int, str, np.ndarray, np.dtype]:
    """
    Extracts data from an MRC format into HDF5

    Arguments
    ---------
        files : a list of strings or paths
            A list of MRC files.
        dtype : string, optional
            Convert the original data from MRC to this type in HDF5.
            Can be: 'uint16', 'uint32', 'uint64', 'int16', 'int32', 'int64',
                    'float32', 'float64'.
            Default is None, in which case the original data type will be
            preserved during conversion.

    Returns
    -------
        hdf5_file :  string
            Name of the output HDF5 file.

    Converts MRC data to HDF5. The input can be either a list of individual
    MRC images, or a single MRC file with a stack of images. In the first
    case, the function assumes that all MRC files end with an indexing number
    (e.g. some_basename_00001.mrc) and removes everything after the last '_'
    (e.g. the output is some_basename.h5). In the second case (a single MRC
    input file) the function only replaces the '.mrc' extension with '.h5'.
    The HDF5 output contains a 3D array (saved in the field
    '/entry/data/data'), where the first index enumerates the images.
    """

    # Remove everything after the last '_' from the file name (the indexing)
    out_file = os.path.basename(files[0])

    ends_with_number = re.search(r"_(\d+)\.mrc", out_file)

    if ends_with_number:
        out_file = out_file.rsplit("_", 1)[0] + ".h5"
    else:
        out_file = out_file.replace(".mrc", ".h5")

    mrc_files = []

    # Filter only MRC files from the input
    for file in files:
        path = os.path.abspath(file)
        if path.endswith(".mrc"):
            mrc_files.append(file)

    n = len(mrc_files)

    test_file = mrcfile.open(mrc_files[0], mode="r")
    data_shape = test_file.data.shape

    if not dtype:
        dtype = test_file.data.dtype
    else:
        dtype = np.dtype(dtype)  # Convert the string to dtype

    test_file.close()

    # Input is a single MRC file with a stack of images
    if (len(data_shape) == 3) and (n == 1):

        with h5py.File(out_file, "w") as hdf5_file:

            mrc = mrcfile.open(files[0], mode="r")

            bs = hdf5plugin.Bitshuffle
            dataset_shape = (data_shape[0], data_shape[1], data_shape[2])
            dataset = hdf5_file.create_dataset(
                "data_temp",
                shape=dataset_shape,
                dtype=dtype,
                **bs(clevel=3, cname="lz4"),
            )

            group = hdf5_file.create_group("entry")
            group.attrs["NX_class"] = np.bytes_("NXentry")
            data_group = group.create_group("data")
            data_group.attrs["NX_class"] = np.bytes_("NXdata")

            compressed_data = hdf5_file.create_dataset(
                "/entry/data/data",
                shape=dataset_shape,
                dtype=dtype,
                **bs(clevel=3, cname="lz4"),
            )

            dataset[:, :, :] = mrc.data
            mrc.close()

            compressed_data[...] = dataset[...]
            del hdf5_file["data_temp"]

            return out_file

    # Input is a list of MRC files containing single images
    elif (len(data_shape) == 2) and (n >= 1):

        with h5py.File(out_file, "w") as hdf5_file:
            dataset_shape = (n, data_shape[0], data_shape[1])
            dataset = hdf5_file.create_dataset(
                "data_temp", shape=dataset_shape, dtype=dtype
            )

            group = hdf5_file.create_group("entry")
            group.attrs["NX_class"] = np.bytes_("NXentry")
            data_group = group.create_group("data")
            data_group.attrs["NX_class"] = np.bytes_("NXdata")

            field = "/entry/data/data"
            compressed_data = hdf5_file.create_dataset(
                field, shape=dataset_shape, dtype=dtype, **hdf5plugin.LZ4()
            )

            for i, file in enumerate(mrc_files):
                logger.info("Reading image %d:  %s" % (i, file))
                mrc = mrcfile.open(file, mode="r")
                data = np.array(mrc.data, dtype=dtype)

                if len(data.shape) > 2:
                    msg = "MRC file contains more than a single image\n"
                    msg += f"  File: {file}"
                    raise ValueError(msg)

                dataset[i, :, :] = data
                mrc.close()

            compressed_data[...] = dataset[...]
            del hdf5_file["data_temp"]

            return out_file
    else:
        msg = "The converter expects either a list of MRC images\n"
        msg += "or a single MRC file with a stack of images."
        raise ValueError(msg)
