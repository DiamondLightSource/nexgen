from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_utils import Axis, TransformationType
from nexgen.nxs_write.NXclassWriters import (
    write_NXcollection,
    write_NXcoordinate_system_set,
    write_NXdata,
    write_NXdatetime,
    write_NXdetector,
    write_NXdetector_module,
    write_NXentry,
    write_NXinstrument,
    write_NXnote,
    write_NXsample,
)

test_module = {"fast_axis": [1, 0, 0], "slow_axis": [0, 1, 0]}

test_goniometer_axes = {
    "axes": ["omega", "sam_z", "sam_y"],
    "depends": [".", "omega", "sam_z"],
    "vectors": [
        (-1, 0, 0),
        (0, -1, 0),
        (-1, 0, 0),
    ],
    "types": [
        "rotation",
        "translation",
        "translation",
    ],
    "units": ["deg", "mm", "mm"],
    "offsets": [(0, 0, 0), (0, 0, 0), (0, 0, 0)],
    "starts": [0, 0, 0],
    "ends": [90, 0, 0],
    "increments": [1, 0, 0],
}

test_eiger = {
    "mode": "images",
    "description": "Eiger 2X 9M",
    "detector_type": "Pixel",
    "sensor_material": "CdTe",
    "sensor_thickness": "0.750mm",
    "flatfield": None,
    "pixel_mask": None,
    "overload": 50649,  # "_dectris/countrate_correction_count_cutoff",
    "underload": -1,
    "pixel_size": ["0.075mm", "0.075mm"],
    "beam_center": [1590.7, 1643.7],
    "image_size": [3262, 3108],  # (slow, fast)
    "axes": ["det_z"],
    "depends": ["."],
    "vectors": [(0, 0, 1)],
    "types": ["translation"],
    "units": ["mm"],
    "starts": [500],
    "exposure_time": 0.01,
}

test_source = {
    "name": "Diamond Light Source",
    "short_name": "DLS",
}


def test_given_no_data_files_when_write_NXdata_then_assert_error():
    mock_hdf5_file = MagicMock()
    with pytest.raises(OSError):
        write_NXdata(mock_hdf5_file, [], {}, "", "", [])


def test_write_NXentry(dummy_nexus_file):
    entry = write_NXentry(dummy_nexus_file)

    assert dummy_nexus_file["/entry/"].attrs["NX_class"] == b"NXentry"
    assert dummy_nexus_file["/entry/"].attrs["default"] == b"data"
    assert dummy_nexus_file["/entry/"].attrs["version"] == b"1.0"

    assert "definition" in entry.keys()
    assert dummy_nexus_file["/entry/definition"][()] == b"NXmx"


def test_given_no_data_type_specified_when_write_NXdata_then_exception_raised(
    dummy_nexus_file,
):
    osc_scan = {"omega": np.arange(0, 90, 1)}
    with pytest.raises(ValueError):
        write_NXdata(
            dummy_nexus_file,
            [Path("tmp")],
            test_goniometer_axes,
            "",
            osc_scan,
        )


def test_given_one_data_file_when_write_NXdata_then_data_in_file(
    dummy_nexus_file,
):
    osc_scan = {"omega": np.arange(0, 90, 1)}
    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        "images",
        osc_scan,
    )
    assert dummy_nexus_file["/entry/data"].attrs["NX_class"] == b"NXdata"
    assert "data_000001" in dummy_nexus_file["/entry/data"]


def test_given_scan_axis_when_write_NXdata_then_axis_in_data_entry_with_correct_data_and_attributes(
    dummy_nexus_file,
):
    test_axis = "omega"
    test_scan_range = np.arange(0, 90, 1)
    axis_entry = f"/entry/data/{test_axis}"
    osc_scan = {test_axis: test_scan_range}

    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        "images",
        osc_scan,
    )

    assert test_axis in dummy_nexus_file["/entry/data"]
    assert_array_equal(test_scan_range, dummy_nexus_file[axis_entry][:])
    assert dummy_nexus_file[axis_entry].attrs["depends_on"] == b"."
    assert dummy_nexus_file[axis_entry].attrs["transformation_type"] == b"rotation"
    assert dummy_nexus_file[axis_entry].attrs["units"] == b"deg"
    assert_array_equal(dummy_nexus_file[axis_entry].attrs["vector"][:], [-1.0, 0.0, 0])


def test_given_scan_axis_when_write_NXsample_then_scan_axis_data_copied_from_data_group_as_well_as_increment_set_and_end(
    dummy_nexus_file,
):
    test_axis = "omega"
    test_scan_range = [0, 1, 2]
    axis_entry = f"/entry/sample/sample_{test_axis}/{test_axis}"
    osc_scan = {test_axis: test_scan_range}

    # Doing this to write the scan axis data into the data group
    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        "images",
        osc_scan,
    )

    write_NXsample(
        dummy_nexus_file,
        test_goniometer_axes,
        "images",
        osc_scan,
    )

    assert f"sample_{test_axis}" in dummy_nexus_file["/entry/sample"]
    assert_array_equal(test_scan_range, dummy_nexus_file[axis_entry][:])
    assert dummy_nexus_file[axis_entry].attrs["depends_on"] == b"."
    assert dummy_nexus_file[axis_entry].attrs["transformation_type"] == b"rotation"
    assert dummy_nexus_file[axis_entry].attrs["units"] == b"deg"
    assert_array_equal(dummy_nexus_file[axis_entry].attrs["vector"][:], [-1, 0, 0])
    assert_array_equal(dummy_nexus_file[axis_entry + "_increment_set"][()], 1)
    # assert_array_equal(dummy_nexus_file[axis_entry + "_increment_set"][:], [1] * 3)
    assert dummy_nexus_file[axis_entry + "_end"][1] == 2


def test_sample_depends_on_written_correctly_in_NXsample(dummy_nexus_file):
    test_axis = "omega"
    test_scan_range = [0, 1, 2]
    osc_scan = {test_axis: test_scan_range}

    # Doing this to write the scan axis data into the data group
    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        "images",
        osc_scan,
    )

    write_NXsample(
        dummy_nexus_file,
        test_goniometer_axes,
        "images",
        osc_scan,
        sample_depends_on=test_axis,
    )

    assert "depends_on" in dummy_nexus_file["/entry/sample"]
    assert (
        dummy_nexus_file["/entry/sample/depends_on"][()]
        == b"/entry/sample/transformations/omega"
    )


def test_sample_depends_on_written_correctly_in_NXsample_when_value_not_passed(
    dummy_nexus_file,
):
    test_axis = "omega"
    test_scan_range = [0, 1, 2]
    osc_scan = {test_axis: test_scan_range}

    test_depends = f"/entry/sample/transformations/{test_goniometer_axes['axes'][-1]}"

    # Doing this to write the scan axis data into the data group
    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        "images",
        osc_scan,
    )

    write_NXsample(
        dummy_nexus_file,
        test_goniometer_axes,
        "images",
        osc_scan,
    )

    assert "depends_on" in dummy_nexus_file["/entry/sample"]
    assert dummy_nexus_file["/entry/sample/depends_on"][()] == test_depends.encode()


def test_sample_details_in_NXsample(dummy_nexus_file):

    test_details = {"name": b"test_sample", "temperature": "25C"}
    test_axis = "omega"
    test_scan_range = [0, 1, 2]
    osc_scan = {test_axis: test_scan_range}

    # Doing this to write the scan axis data into the data group
    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        test_goniometer_axes,
        "images",
        osc_scan,
    )

    write_NXsample(
        dummy_nexus_file,
        test_goniometer_axes,
        "images",
        osc_scan,
        sample_details=test_details,
    )

    assert "name" in dummy_nexus_file["/entry/sample"]
    assert "temperature" in dummy_nexus_file["/entry/sample"]
    assert dummy_nexus_file["/entry/sample/name"][()] == test_details["name"]
    assert (
        dummy_nexus_file["/entry/sample/temperature"][()]
        == test_details["temperature"].encode()
    )


def test_given_module_offset_of_1_when_write_NXdetector_module_then_fast_and_slow_axis_depends_on_module_offset(
    dummy_nexus_file,
):
    test_module["module_offset"] = "1"
    write_NXdetector_module(dummy_nexus_file, test_module, [10, 10], [0.1, 0.1], [0, 0])

    module_nexus_path = "/entry/instrument/detector/module/"
    for axis in ["slow_pixel_direction", "fast_pixel_direction"]:
        assert len(dummy_nexus_file[module_nexus_path + axis].attrs.keys()) == 6
        assert (
            dummy_nexus_file[module_nexus_path + axis].attrs["depends_on"]
            == b"/entry/instrument/detector/module/module_offset"
        )


def test_write_NXdatetime_from_ISO8601str(dummy_nexus_file):
    # Check that ISO8601 strings are accepted and written to file
    entry_path = "/entry/"
    timestamp_str = "2022-03-31T10:30:42Z"
    write_NXdatetime(dummy_nexus_file, timestamp_str, "start_time")

    assert "start_time" in dummy_nexus_file[entry_path].keys()


def test_write_NXdatetime_from_not_ISO8601str(dummy_nexus_file):
    entry_path = "/entry/"
    timestamp_str = datetime.now().strftime("%a %b %d %Y %H:%M:%S")

    write_NXdatetime(dummy_nexus_file, timestamp_str, "start_time")

    assert "start_time" in dummy_nexus_file[entry_path].keys()
    val = dummy_nexus_file[entry_path + "start_time"][()].decode()
    assert val.endswith("Z")


def test_write_NXdatetime_from_datetime(dummy_nexus_file):
    # Check that datetime objects are accepted and written to file
    entry_path = "/entry/"
    end_ts = datetime.fromisoformat("2022-03-31T16:30:32")
    write_NXdatetime(dummy_nexus_file, end_ts, "end_time")

    assert "end_time" in dummy_nexus_file[entry_path].keys()
    val = dummy_nexus_file[entry_path + "end_time"][()].decode()
    assert val.endswith("Z")


def test_write_NXdatetime_writes_nothing_if_wrong_dset_requested(dummy_nexus_file):
    entry_path = "/entry/"
    write_NXdatetime(dummy_nexus_file, "", "no_time")

    assert "no_time" not in dummy_nexus_file[entry_path].keys()


def test_NXdatetime_exits_before_writing_if_timestamp_is_None(dummy_nexus_file):
    entry_path = "/entry/"
    write_NXdatetime(dummy_nexus_file, None, "end_time_estimated")

    assert entry_path + "end_time_estimated" not in dummy_nexus_file.keys()


def test_write_NXnote_in_given_location(dummy_nexus_file):
    loc_path = "/entry/source/pump_probe/"
    info = {"pump_status": True, "pump_exp": 0.001}
    write_NXnote(dummy_nexus_file, loc_path, info)

    assert "pump_status" in dummy_nexus_file[loc_path].keys()
    assert "pump_exp" in dummy_nexus_file[loc_path].keys()
    assert_array_equal(dummy_nexus_file[loc_path + "pump_exp"][()], 0.001)


def test_write_NXcoordinate_system_set(dummy_nexus_file):
    bases = {
        "x": Axis("x", ".", TransformationType.TRANSLATION, (0, 0, 1)),
        "y": Axis("y", "x", TransformationType.TRANSLATION, (0, 0, 0)),
        "z": Axis("z", "y", TransformationType.TRANSLATION, (-1, 0, 0)),
    }

    write_NXcoordinate_system_set(
        dummy_nexus_file, "new_coord_system", bases, (1, 1, 0)
    )

    assert "coordinate_system_set" in dummy_nexus_file["/entry/"].keys()

    loc = "/entry/coordinate_system_set/transformations/"
    assert dummy_nexus_file[loc + "depends_on"][()] == b"."
    assert "x" in dummy_nexus_file[loc].keys()
    assert "y" in dummy_nexus_file[loc].keys()
    assert "z" in dummy_nexus_file[loc].keys()
    assert_array_equal(dummy_nexus_file[loc + "origin"][()], (1, 1, 0))
    assert_array_equal(dummy_nexus_file[loc + "x"][()], 1)
    assert_array_equal(dummy_nexus_file[loc + "y"].attrs["vector"], [0, 0, 0])


def test_write_NXcollection_for_images(dummy_nexus_file):
    nxdet = dummy_nexus_file.require_group("/entry/instrument/detector")
    test_detector_spec = {
        "description": "eiger",
        "image_size": [512, 1028],
        "software_version": "0.0.0",
    }
    write_NXcollection(nxdet, test_detector_spec, ("images", 10))

    spec = "/entry/instrument/detector/detectorSpecific/"
    assert dummy_nexus_file[spec + "software_version"][()] == b"0.0.0"
    assert_array_equal(dummy_nexus_file[spec + "nimages"][()], 10)
    assert_array_equal(
        dummy_nexus_file[spec + "x_pixels"][()], test_detector_spec["image_size"][1]
    )
    assert_array_equal(
        dummy_nexus_file[spec + "y_pixels"][()], test_detector_spec["image_size"][0]
    )


def test_write_NXcollection_for_events(dummy_nexus_file):
    nxdet = dummy_nexus_file.require_group("/entry/instrument/detector")
    test_detector_spec = {
        "description": "Tristan 1M",
        "image_size": [515, 2069],
        "software_version": "0.0.0",
        "detector_tick": "1562.5ps",
        "detector_frequency": "6.4e+08Hz",
        "timeslice_rollover": 18,
    }

    write_NXcollection(nxdet, test_detector_spec, ("events", None))

    spec = "/entry/instrument/detector/detectorSpecific/"
    assert dummy_nexus_file[spec + "software_version"][()] == b"0.0.0"
    assert_array_equal(
        dummy_nexus_file[spec + "timeslice_rollover_bits"][()],
        test_detector_spec["timeslice_rollover"],
    )
    assert_array_equal(dummy_nexus_file[spec + "detector_tick"][()], 1562.5)
    assert dummy_nexus_file[spec + "detector_tick"].attrs["units"] == b"ps"
    assert dummy_nexus_file[spec + "detector_frequency"].attrs["units"] == b"Hz"


def test_write_NXdetector_for_images_without_meta_file(dummy_nexus_file):
    det = "/entry/instrument/detector/"

    write_NXdetector(
        dummy_nexus_file,
        test_eiger,
        ("images", 100),
    )

    # Check some general things
    assert (
        dummy_nexus_file[det + "description"][()] == test_eiger["description"].encode()
    )
    assert dummy_nexus_file[det + "type"][()] == test_eiger["detector_type"].encode()

    assert_array_equal(
        dummy_nexus_file[det + "beam_center_x"][()], test_eiger["beam_center"][0]
    )
    assert dummy_nexus_file[det + "beam_center_y"].attrs["units"] == b"pixels"
    assert_array_equal(dummy_nexus_file[det + "y_pixel_size"], 7.5e-05)
    assert dummy_nexus_file[det + "x_pixel_size"].attrs["units"] == b"m"

    # Check no mask
    assert "pixel_mask" not in list(dummy_nexus_file[det].keys())

    # Check detector axis and distance
    tr = det + "transformations/"
    assert "detector_z" in list(dummy_nexus_file[tr].keys())
    axis_entry = tr + "detector_z/det_z"
    assert_array_equal(test_eiger["starts"], dummy_nexus_file[axis_entry][()])
    assert dummy_nexus_file[axis_entry].attrs["depends_on"] == b"."
    assert dummy_nexus_file[axis_entry].attrs["transformation_type"] == b"translation"
    assert dummy_nexus_file[axis_entry].attrs["units"] == b"mm"
    assert_array_equal(
        dummy_nexus_file[axis_entry].attrs["vector"][()], test_eiger["vectors"][0]
    )

    # Check that distance is in meters instead of mm
    assert_array_equal(
        dummy_nexus_file[det + "distance"], test_eiger["starts"][0] / 1000
    )
    assert dummy_nexus_file[det + "distance"].attrs["units"] == b"m"

    # Check that detector_z has also been written in /detector
    assert "detector_z" in list(dummy_nexus_file[det].keys())


def test_write_NXinstrument(dummy_nexus_file):
    instr = "/entry/instrument/"

    test_source["beamline_name"] = "I03"

    write_NXinstrument(
        dummy_nexus_file,
        {"wavelength": 0.6, "flux": None},
        {"transmission": 10},
        test_source,
    )

    assert "attenuator" in list(dummy_nexus_file[instr].keys())
    assert "beam" in list(dummy_nexus_file[instr].keys())
    assert dummy_nexus_file[instr + "name"][()] == b"DIAMOND BEAMLINE I03"
    assert dummy_nexus_file[instr + "name"].attrs["short_name"] == b"DLS I03"


def test_write_NXinstrument_sets_correct_instrument_name(dummy_nexus_file):
    instr = "/entry/instrument/"

    test_source["beamline_name"] = "eBic"

    write_NXinstrument(
        dummy_nexus_file,
        {"wavelength": 0.001, "flux": None},
        {"transmission": 1},
        test_source,
        "DIAMOND MICROSCOPE",
    )

    assert dummy_nexus_file[instr + "name"][()] == b"DIAMOND MICROSCOPE"
    assert dummy_nexus_file[instr + "name"].attrs["short_name"] == b"DLS eBic"
