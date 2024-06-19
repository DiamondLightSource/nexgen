""" Helper functions for the MRC to Nexus converter """

import os
from math import sqrt

import h5py
import hdf5plugin
import mrcfile
import numpy as np


def cal_wavelength(V0):
    """
    Compute the relativistic electron wavelength from
    the electron acceleration voltage.

    Args:
        V0 (int or float): acceleration voltage for electrons
                           in Volts [V].

    Returns:
        wlen (float): Electron wavelength in Angstroms.

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


def get_metadata(mrc_image, verbatim=True):
    """
    Extract the metadata dictionary from a single MRC file.

    Args:
        mrc_image (Path or str): the MRC file path.

    Returns:
        hd (dict): A dictionary containing metadata
                   from the MRC file.

    The function extracts data from the MRC header and extended
    header dictionaries.
    """

    with mrcfile.open(mrc_image, header_only=True) as mrc:
        h = mrc.header
        try:
            xh = mrc.indexed_extended_header
        except AttributeError:
            # For mrcfile versions older than 1.5.0
            xh = mrc.extended_header
        hd = {}

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
        hd["diffractionPatternRotation"] = xh["Diffraction pattern rotation"][0]
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


def collect_data(files):
    """
    Extract image data from a list of MRC files into a single
    HDF5 (h5) file.

    Args:
        files (list of strings): A list containing names
            of all MRC images.

    Returns:
        n (int): The total number of MRC images.
        out_file (string): Name of the output h5 file.
        angles (1D numpy array of floats): An array containing
            tilt angles of all MRC images (as extracted from the
            MRC metadata).

    The function takes a list of MRC filenames, assuming that each
    filename contains a single diffraction image (as a 2D array),
    and makes a single h5 file containing a 3D array (where the first
    index enumerates the images). The data is saved in the field
    '/entry/data/data/' as an int32 and compressed using the LZ4
    compression method. Note that the original data in the MRC files
    is saved as a floating point number, although the actual data
    consists solely of integers. The function also assumes that all
    MRC files end with an indexing number: like 'basename_00001.mrc',
    in which case the data is saved in 'basename.h5'.
    """

    out_file = files[0].rsplit("_", 1)[0] + ".h5"
    mrc_files = []
    angles = []
    for file in files:
        path = os.path.abspath(file)
        if path.endswith(".mrc"):
            mrc_files.append(file)

    n = len(mrc_files)

    test_file = mrcfile.open(mrc_files[0], mode="r")
    data_shape = test_file.data.shape
    test_file.close()
    if len(data_shape) != 2:
        msg = "The converter works only with individual MRC images"
        raise ValueError(msg)

    with h5py.File(out_file, "w") as hdf5_file:
        dataset_shape = (n, data_shape[0], data_shape[1])
        dataset = hdf5_file.create_dataset(
            "data_temp", shape=dataset_shape, dtype=np.int32
        )

        group = hdf5_file.create_group("entry")
        group.attrs["NX_class"] = np.bytes_("NXentry")
        data_group = group.create_group("data")
        data_group.attrs["NX_class"] = np.bytes_("NXdata")

        compressed_data = hdf5_file.create_dataset(
            "/entry/data/data", shape=dataset_shape, dtype=np.int32, **hdf5plugin.LZ4()
        )

        for i, file in enumerate(mrc_files):
            print(" Reading image %d:  %s" % (i, file))
            mrc = mrcfile.open(file, mode="r")
            data = np.array(mrc.data, dtype=np.int32)
            try:
                xh = mrc.indexed_extended_header
            except AttributeError:
                xh = mrc.extended_header

            if "Alpha tilt" in xh.dtype.names:
                angles.append(xh["Alpha tilt"][0])
            else:
                angles.append(None)
            dataset[i, :, :] = data
            mrc.close()

        compressed_data[...] = dataset[...]
        del hdf5_file["data_temp"]

        return n, out_file, np.array(angles)
