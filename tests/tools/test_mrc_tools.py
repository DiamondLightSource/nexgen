import logging
import os

import mrcfile
import numpy as np

from nexgen.tools.mrc_tools import cal_wavelength, get_metadata, to_hdf5_data_file

logger = logging.getLogger("nexgen.ED_mrc_to_nexus")


def test_cal_wavelength():

    a = 0.025082356047905176
    epsilon = 1.0e-15
    assert abs(cal_wavelength(200000) - a) < epsilon


def test_get_metadata():

    make_mrc_file("images.mrc")
    h = get_metadata("images.mrc")
    assert isinstance(h, dict)

    os.remove("images.mrc")


def test_collect_data():

    make_mrc_file("images_00001.mrc")
    make_mrc_file("images_00002.mrc")

    files = ["images_00001.mrc", "images_00002.mrc"]
    hdf5_file = to_hdf5_data_file(files, logger)
    assert hdf5_file == "images.h5"
    assert os.path.exists("images.h5")

    os.remove("images_00001.mrc")
    os.remove("images_00002.mrc")
    os.remove("images.h5")


def make_mrc_file(filename):

    images = np.zeros((1, 1), dtype=np.int16)

    with mrcfile.new(filename, overwrite=True) as mrc:
        mrc.set_data(images)

        mrc.voxel_size = 1.0  # example voxel size in angstroms
        mrc.header.nxstart = 0
        mrc.header.nystart = 0
        mrc.header.nzstart = 0
        mrc.header.nx = 1
        mrc.header.ny = 1
        mrc.header.nz = 1
        mrc.header.mx = 1
        mrc.header.my = 1
        mrc.header.mz = 1
        mrc.header.exttyp = np.array("CCP4", dtype="S")
