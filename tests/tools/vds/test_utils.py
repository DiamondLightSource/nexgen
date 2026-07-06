import tempfile

import h5py
import numpy as np
import pytest

from nexgen.tools.vds_tools.utils import (
    define_vds_dtype_from_bit_depth,
    find_datasets_in_file,
)


def test_find_datasets_in_file(nexus_file_with_single_dataset):
    nxdata = nexus_file_with_single_dataset["/entry/data"]
    dsets = find_datasets_in_file(nxdata)
    assert len(dsets) == 1
    assert dsets[0] == "data_0001"


def test_find_multiple_datasets_in_file(nexus_file_with_multiple_datasets):
    nxdata = nexus_file_with_multiple_datasets["/entry/data"]
    dsets = find_datasets_in_file(nxdata)
    assert len(dsets) == 2
    assert dsets[0] == "data_0001" and dsets[1] == "data_0002"


def test_find_datasets_fails_if_no_links_in_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    test_nexus_file["/entry/data/data_0001"] = [0, 0, 0]
    with pytest.raises(KeyError):
        find_datasets_in_file(test_nexus_file)


@pytest.mark.parametrize(
    "bit_depth, expected_dtype", [(8, np.uint8), (16, np.uint16), (32, np.uint32)]
)
def test_vds_dtype_from_input(bit_depth, expected_dtype):
    d = define_vds_dtype_from_bit_depth(bit_depth)

    assert d == expected_dtype
