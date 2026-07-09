import tempfile
from unittest.mock import MagicMock

import h5py

from nexgen.tools.vds_w_tools import (
    jungfrau_vds_writer,
)


def test_jungfrau_vds_writer_with_external_dsets():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    test_nexus_file["/entry/data/data_0001"] = MagicMock()
    source_dsets = ["path/to/file1", "path/to/file2"]
    jungfrau_vds_writer(
        test_nexus_file,
        (100, 1066, 1030),
        source_dsets=source_dsets,
    )
    assert "data" in list(test_nexus_file["/entry/data"].keys())


def test_jungfrau_vds_writer_not_failing_if_no_external_dsets():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    test_nexus_file["/entry/data/data_0001"] = h5py.ExternalLink("f1le1", "data")
    test_nexus_file["/entry/data/data_0002"] = h5py.ExternalLink("f1le2", "data")
    jungfrau_vds_writer(
        test_nexus_file,
        (100, 1066, 1030),
    )
    assert "data" in list(test_nexus_file["/entry/data"].keys())
