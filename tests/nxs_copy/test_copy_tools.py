import tempfile

import h5py
import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_copy.copy_utils import (
    check_and_fix_det_axis,
    convert_scan_axis,
    h5str,
    identify_tristan_scan_axis,
    is_chipmap_in_tristan_nxs,
)
from nexgen.nxs_write.nxclass_writers import write_NXentry, write_NXnote
from nexgen.nxs_write.write_utils import create_attributes

test_chipmap = {"01": (0, 0)}


def test_h5str():
    assert h5str("string_obj") == "string_obj"
    assert h5str(b"bytes_obj") == "bytes_obj"


@pytest.fixture
def dummy_nexus_file():
    test_hdf_file = tempfile.TemporaryFile()
    test_nexus_file = h5py.File(test_hdf_file, "w")
    yield test_nexus_file


def test_identify_tristan_scan_axis(dummy_nexus_file):
    nxentry = write_NXentry(dummy_nexus_file)
    nxdata = nxentry.require_group("data")
    axis1 = nxdata.create_dataset("omega", data=(0, 0))
    create_attributes(
        axis1, ("transformation_type", "vector"), (b"rotation", [0, 0, 1])
    )
    axis2 = nxdata.create_dataset("sam_x", data=(0,))
    create_attributes(axis2, ("transformation_type",), ("translation",))
    nxdata.create_dataset("data", data=b"Some dummy data")

    ax, ax_attrs = identify_tristan_scan_axis(dummy_nexus_file)
    assert ax == "omega"
    assert len(ax_attrs) > 0
    assert ax_attrs["transformation_type"] == "rotation"
    assert_array_equal(ax_attrs["vector"], [0, 0, 1])


def test_convert_scan_axis(dummy_nexus_file):
    scan_range = np.arange(0, 2, 0.2)
    nxentry = write_NXentry(dummy_nexus_file)
    nxdata = nxentry.require_group("data")
    nxsample = nxentry.require_group("sample")
    nxtr = nxsample.require_group("transformations")
    axis = nxdata.create_dataset("omega", data=scan_range)
    create_attributes(axis, ("transformation_type", "vector"), (b"rotation", [0, 0, 1]))
    nxsample.require_group("sample_omega")
    nxsample["sample_omega"].create_dataset("omega", data=(0, 2))
    nxtr["omega"] = nxsample["sample_omega/omega"]

    convert_scan_axis(nxsample, nxdata, "omega", scan_range)
    assert_array_equal(nxsample["sample_omega/omega"], scan_range)
    assert_array_equal(nxtr["omega"], scan_range)
    assert (
        "omega_end" in nxsample["sample_omega"].keys()
        and "omega_increment_set" in nxsample["sample_omega"].keys()
    )
    assert_array_equal(nxsample["sample_omega/omega_increment_set"][()], 0.2)
    assert_array_equal(nxsample["sample_omega/omega_end"][()], scan_range + 0.2)


def test_check_and_fix_det_z(dummy_nexus_file):
    nxentry = write_NXentry(dummy_nexus_file)
    nxentry.create_dataset("instrument/detector/distance", data=b"150.")
    nxdet_z_grp = nxentry.require_group(
        "instrument/detector/transformations/detector_z"
    )
    det_z = nxdet_z_grp.create_dataset("det_z", data=b"150.")
    create_attributes(det_z, ("transformation_type", "units"), ("translation", "mm"))

    check_and_fix_det_axis(dummy_nexus_file)
    fixed_det = dummy_nexus_file[
        "/entry/instrument/detector/transformations/detector_z/det_z"
    ]
    assert_array_equal(fixed_det[()], np.array([150.0]))
    assert det_z.attrs["units"] == b"mm"
    assert det_z.attrs["transformation_type"] == b"translation"
    fixed_dist = dummy_nexus_file["/entry/instrument/detector/distance"]
    assert fixed_dist[()] == 0.150
    assert fixed_dist.attrs["units"] == b"m"


def test_find_chipmap(dummy_nexus_file):
    test_map = {"chipmap": str(test_chipmap)}
    nxentry = write_NXentry(dummy_nexus_file)
    write_NXnote(dummy_nexus_file, "/entry/source/notes", test_map)

    assert is_chipmap_in_tristan_nxs(dummy_nexus_file) is True
    assert is_chipmap_in_tristan_nxs(nxentry, loc="source/notes/chipmap") is True
