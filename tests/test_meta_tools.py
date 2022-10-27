import tempfile

import h5py
import numpy as np
import pytest

from nexgen.tools.Metafile import DectrisMetafile, TristanMetafile
from nexgen.tools.MetaReader import overwrite_beam

dummy_config = '{"nimages": 10, "ntrigger": 1}'

test_beam = {"wavelength": 0.0}


def test_Tristan_meta_file():
    test_hdf_file = tempfile.NamedTemporaryFile(suffix=".h5", delete=True)
    with h5py.File(test_hdf_file, "w") as test_meta_file:
        test_meta_file["ts_qty_module00"] = np.zeros(2)
        test_meta_file["ts_qty_module01"] = np.zeros(2)
        assert TristanMetafile(test_meta_file).find_number_of_modules() == 2
        assert TristanMetafile(test_meta_file).find_software_version() is None

    assert TristanMetafile.isTristan(test_hdf_file.name)


@pytest.fixture
def dummy_eiger_meta_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_meta_file = h5py.File(test_hdf_file, "w")
    test_meta_file["config"] = '{"nimages": 10, "ntrigger": 1}'
    test_meta_file["_dectris/wavelength"] = np.array([0.6])
    # test_meta_file[]
    yield test_meta_file


def test_Eiger_meta_file(dummy_eiger_meta_file):
    meta = DectrisMetafile(dummy_eiger_meta_file)
    assert meta.hasDectrisGroup
    assert meta.hasMask is False and meta.hasFlatfield is False
    assert meta.hasConfig
    assert meta.read_config_dset() == {"nimages": 10, "ntrigger": 1}
    assert meta.get_number_of_images() == 10


def test_overwrite_beam(dummy_eiger_meta_file):
    overwrite_beam(dummy_eiger_meta_file, "Eiger", test_beam)
    assert test_beam["wavelength"] == 0.6
