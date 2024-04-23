from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from nexgen.nxs_write.nxclass_writers import write_NXtransformations
from nexgen.nxs_write.write_utils import (
    add_sample_axis_groups,
    calculate_estimated_end_time,
    calculate_origin,
    create_attributes,
    find_number_of_images,
    mask_and_flatfield_writer,
    mask_and_flatfield_writer_for_event_data,
    set_dependency,
    write_compressed_copy,
)

test_module = {"fast_axis": [1, 0, 0], "slow_axis": [0, 1, 0]}


def test_create_attributes(dummy_nexus_file):
    nxentry = dummy_nexus_file.require_group("/entry/")
    create_attributes(nxentry, ("NX_class", "version"), ("NXentry", "0.0"))

    assert dummy_nexus_file["/entry/"].attrs["NX_class"] == b"NXentry"
    assert dummy_nexus_file["/entry/"].attrs["version"] == b"0.0"


def test_set_dependency(mock_goniometer):
    # Check that the end of the dependency chain always gets set to b"."
    assert set_dependency(".", "/entry/sample/transformations/") == b"."
    assert set_dependency(mock_goniometer.axes_list[0].depends) == b"."
    assert set_dependency("whatever") != b"."

    # Check the path
    assert (
        set_dependency(mock_goniometer.axes_list[-1].depends, "/entry")
        == b"/entry/sam_z"
    )


def test_calculate_origin():
    # Check that the default return offset value is 1.0
    beam_center = [1000, 2000]
    pixel_size = [5e-05, 5e-05]
    vec1, val1 = calculate_origin(
        beam_center, pixel_size, test_module["fast_axis"], test_module["slow_axis"]
    )
    assert len(vec1) == 3
    assert val1 == 1.0


def test_find_number_of_images_returns_0_if_no_file_passed():
    n_images = find_number_of_images([])
    assert n_images == 0


def test_mask_external_link_writer(dummy_nexus_file):
    nxdet_path = "/entry/instrument/detector/"
    nxdetector = dummy_nexus_file.require_group(nxdet_path)
    test_mask = "path/to/mask/filename"
    mask_and_flatfield_writer(nxdetector, "pixel_mask", test_mask, False)

    assert not dummy_nexus_file[nxdet_path + "pixel_mask_applied"][()]


@patch("nexgen.nxs_write.write_utils.write_compressed_copy")
def test_flatfield_dataset_writer(fake_copy_write, dummy_nexus_file):
    nxdet_path = "/entry/instrument/detector/"
    nxdetector = dummy_nexus_file.require_group(nxdet_path)
    test_flatfield = np.ndarray(shape=(3, 3))
    mask_and_flatfield_writer(nxdetector, "flatfield", test_flatfield, True)

    assert dummy_nexus_file[nxdet_path + "flatfield_applied"][()]
    fake_copy_write.assert_called_once()


def test_mask_flatfield_writer_for_events(dummy_nexus_file):
    nxdet_path = "/entry/instrument/detector/"
    nxdetector = dummy_nexus_file.require_group(nxdet_path)

    mask_and_flatfield_writer_for_event_data(
        nxdetector,
        "pixel_mask",
        "path/to/mask.h5",
        False,
        Path(""),
    )

    assert "pixel_mask" in list(dummy_nexus_file[nxdet_path].keys())
    assert "pixel_mask_applied" in list(dummy_nexus_file[nxdet_path].keys())


def test_if_flafield_is_None_nothing_written_for_events(dummy_nexus_file):
    nxdet_path = "/entry/instrument/detector/"
    nxdetector = dummy_nexus_file.require_group(nxdet_path)

    mask_and_flatfield_writer_for_event_data(
        nxdetector,
        "flatfield",
        None,
        False,
        Path(""),
    )

    assert "flatfield" not in list(dummy_nexus_file[nxdet_path].keys())


def test_write_copy_raises_error_if_both_array_and_file():
    with pytest.raises(ValueError):
        write_compressed_copy("", "", np.array([0.0]), "filename")


def test_calculate_estimated_end_time_from_iso_string():
    timestamp_str = "2023-11-15T10:30:42Z"
    est_end_time = calculate_estimated_end_time(timestamp_str, 10)
    assert est_end_time == "2023-11-15T10:30:52Z"


def test_calculate_estimated_end_time_from_datetime():
    timestamp = datetime.strptime("2023-11-15T10:30:42", "%Y-%m-%dT%H:%M:%S")
    est_end_time = calculate_estimated_end_time(timestamp, 20)
    assert est_end_time == "2023-11-15T10:31:02Z"


def test_add_non_standard_fields_to_NXsample(dummy_nexus_file, mock_goniometer):
    nxsample_path = "/entry/sample"
    nxsample = dummy_nexus_file.require_group(nxsample_path)
    write_NXtransformations(nxsample, mock_goniometer.axes_list, mock_goniometer.scan)
    add_sample_axis_groups(nxsample, mock_goniometer.axes_list)

    assert "sample_omega" in list(dummy_nexus_file[nxsample_path].keys())
    assert "sample_z" in list(dummy_nexus_file[nxsample_path].keys())
    assert "omega_increment_set" in list(
        dummy_nexus_file[nxsample_path]["sample_omega"]
    )
