from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from nexgen.nxs_utils import (
    Axis,
    EigerDetector,
    Facility,
    Goniometer,
    Source,
    TransformationType,
    TristanDetector,
)
from nexgen.nxs_write.nxclass_writers import (
    write_NXattenuator,
    write_NXbeam,
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
    write_NXsource,
    write_NXtransformations,
)

test_module = {"fast_axis": [1, 0, 0], "slow_axis": [0, 1, 0]}


def test_given_no_data_files_when_write_NXdata_then_assert_error():
    mock_hdf5_file = MagicMock()
    with pytest.raises(OSError):
        write_NXdata(mock_hdf5_file, [], "")


def test_write_NXentry(dummy_nexus_file):
    entry = write_NXentry(dummy_nexus_file)

    assert dummy_nexus_file["/entry/"].attrs["NX_class"] == b"NXentry"
    assert dummy_nexus_file["/entry/"].attrs["default"] == b"data"
    assert dummy_nexus_file["/entry/"].attrs["version"] == b"1.0"

    assert "definition" in entry.keys()
    assert dummy_nexus_file["/entry/definition"][()] == b"NXmx"


def test_write_NXSource(dummy_nexus_file, mock_source):
    write_NXsource(dummy_nexus_file, mock_source)

    assert dummy_nexus_file["/entry/source/name"][()] == b"Diamond Light Source"
    assert dummy_nexus_file["/entry/source/name"].attrs["short_name"] == b"DLS"
    assert "probe" not in dummy_nexus_file["/entry/source"].keys()


def test_write_NXSource_with_probe(dummy_nexus_file, mock_source):
    mock_source.probe = "electron"
    write_NXsource(dummy_nexus_file, mock_source)

    assert dummy_nexus_file["/entry/source/probe"][()] == b"electron"


def test_write_NXtransformations_for_detector_axes(dummy_nexus_file):
    det_axes = [
        Axis("two_theta", ".", "rotation", (0, 0, -1), start_pos=90),
        Axis("det_z", "Two_theta", "translation", (0, 0, 1), start_pos=500),
    ]
    nxdet = dummy_nexus_file.require_group("/entry/instrument/detector/")
    write_NXtransformations(nxdet, det_axes)

    assert "transformations" in nxdet.keys()
    assert (
        "det_z" in nxdet["transformations"].keys()
        and "two_theta" in nxdet["transformations"].keys()
    )
    assert_array_equal(nxdet["transformations/det_z"][()], 500)
    assert_array_equal(nxdet["transformations/two_theta"][()], 90)


def test_write_NXtransformations_for_sample_with_rotation_scan(
    dummy_nexus_file, mock_goniometer
):
    nxsample = dummy_nexus_file.require_group("/entry/sample/")
    write_NXtransformations(nxsample, mock_goniometer.axes_list, mock_goniometer.scan)

    assert "transformations" in nxsample.keys()
    assert_array_equal(nxsample["transformations/omega"][()], np.arange(0, 90, 1))
    assert (
        "omega_increment_set" in nxsample["transformations"].keys()
        and "omega_end" in nxsample["transformations"].keys()
    )
    assert_array_equal(nxsample["transformations/sam_z"][()], 0.0)


def test_write_NXtransformations_for_sample_for_events(dummy_nexus_file):
    axes_list = [Axis("phi", ".", "rotation", (0, 0, -1), start_pos=10)]
    test_scan = {"phi": (10, 12)}
    test_gonio = Goniometer(axes_list, test_scan)
    nxsample = dummy_nexus_file.require_group("/entry/sample/")
    write_NXtransformations(nxsample, test_gonio.axes_list, test_gonio.scan, "events")

    assert "phi_end" not in nxsample["transformations"].keys()
    assert_array_equal(nxsample["transformations/phi"], test_scan["phi"])


def test_given_no_data_type_specified_when_write_NXdata_then_exception_raised(
    dummy_nexus_file,
):
    with pytest.raises(ValueError):
        write_NXdata(
            dummy_nexus_file,
            [Path("tmp")],
            "",
        )


def test_given_one_data_file_when_write_NXdata_then_data_in_file(dummy_nexus_file):
    write_NXdata(
        dummy_nexus_file,
        [Path("tmp")],
        "images",
        "omega",
    )
    assert dummy_nexus_file["/entry/data"].attrs["NX_class"] == b"NXdata"
    assert dummy_nexus_file["/entry/data"].attrs["axes"] == b"omega"
    assert dummy_nexus_file["/entry/data"].attrs["omega_indices"] == [0]
    assert "data_000001" in dummy_nexus_file["/entry/data"]


def test_given_scan_axis_when_write_NXsample_then_scan_axis_data_written_and_link_to_NXdata_created(
    dummy_nexus_file, mock_goniometer
):
    test_axis = "omega"
    test_scan_range = [0, 1, 2]
    axis_entry = f"/entry/sample/transformations/{test_axis}"
    osc_scan = {test_axis: test_scan_range}

    write_NXsample(
        dummy_nexus_file,
        mock_goniometer.axes_list,
        "images",
        osc_scan,
    )

    assert "transformations" in dummy_nexus_file["/entry/sample"]
    assert_array_equal(test_scan_range, dummy_nexus_file[axis_entry][:])
    assert dummy_nexus_file[axis_entry].attrs["depends_on"] == b"."
    assert dummy_nexus_file[axis_entry].attrs["transformation_type"] == b"rotation"
    assert dummy_nexus_file[axis_entry].attrs["units"] == b"deg"
    assert_array_equal(dummy_nexus_file[axis_entry].attrs["vector"][:], [-1, 0, 0])
    assert_array_equal(dummy_nexus_file[axis_entry + "_increment_set"][()], 1)
    # assert_array_equal(dummy_nexus_file[axis_entry + "_increment_set"][:], [1] * 3)
    assert dummy_nexus_file[axis_entry + "_end"][1] == 2
    assert f"{test_axis}" in dummy_nexus_file["/entry/data"]


def test_given_reverse_rotation_scan_increment_set_and_axis_end_written_correctly_and_old_fields_not_added(
    dummy_nexus_file,
):
    test_axis = Axis("phi", ".", TransformationType.ROTATION, (0, 0, -1))
    test_rw_scan = {"phi": np.arange(10, 8, -0.5)}
    test_gonio = Goniometer([test_axis], test_rw_scan)

    write_NXsample(
        dummy_nexus_file,
        test_gonio.axes_list,
        "images",
        test_rw_scan,
        sample_depends_on=test_axis.name,
        add_nonstandard_fields=False,
    )

    axis_entry = f"/entry/sample/transformations/{test_axis.name}"

    assert_array_equal(dummy_nexus_file[axis_entry][()], [10.0, 9.5, 9.0, 8.5])
    assert_array_equal(dummy_nexus_file[axis_entry + "_increment_set"][()], -0.5)
    assert_array_equal(dummy_nexus_file[axis_entry + "_end"][()], [9.5, 9.0, 8.5, 8.0])

    assert "sample_phi" not in dummy_nexus_file["/entry/sample"].keys()


def test_sample_depends_on_written_correctly_in_NXsample(
    dummy_nexus_file, mock_goniometer
):
    test_axis = "omega"
    test_scan_range = [0, 1, 2]
    osc_scan = {test_axis: test_scan_range}

    write_NXsample(
        dummy_nexus_file,
        mock_goniometer.axes_list,
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
    mock_goniometer,
):
    test_axis = "omega"
    test_scan_range = [0, 1, 2]
    osc_scan = {test_axis: test_scan_range}

    test_depends = f"/entry/sample/transformations/{mock_goniometer.axes_list[-1].name}"

    write_NXsample(
        dummy_nexus_file,
        mock_goniometer.axes_list,
        "images",
        osc_scan,
    )

    assert "depends_on" in dummy_nexus_file["/entry/sample"]
    assert dummy_nexus_file["/entry/sample/depends_on"][()] == test_depends.encode()


def test_old_sample_groups_added_correctly_to_NXsample_for_rotation_scan(
    dummy_nexus_file,
):
    test_axes = [
        Axis("phi", ".", TransformationType.ROTATION, (0, 0, -1)),
        Axis("sam_z", "phi", TransformationType.TRANSLATION, (0, 0, 1)),
    ]
    test_scan = {"phi": np.arange(0, 1, 0.1)}
    test_gonio = Goniometer(test_axes, test_scan)

    write_NXsample(
        dummy_nexus_file,
        test_gonio.axes_list,
        "images",
        test_scan,
        sample_depends_on=test_axes[0].name,
    )

    sample_path = "/entry/sample/"

    assert "sample_phi" in dummy_nexus_file[sample_path].keys()
    assert (
        "sample_z" in dummy_nexus_file[sample_path].keys()
        and "sam_z" in dummy_nexus_file[sample_path]["sample_z"].keys()
    )
    assert_array_equal(
        dummy_nexus_file[sample_path]["transformations/phi"],
        dummy_nexus_file[sample_path]["sample_phi/phi"][()],
    )


def test_sample_details_in_NXsample(dummy_nexus_file, mock_goniometer):

    test_details = {"name": b"test_sample", "temperature": "25C"}
    test_axis = "omega"
    test_scan_range = [0, 1, 2]
    osc_scan = {test_axis: test_scan_range}

    write_NXsample(
        dummy_nexus_file,
        mock_goniometer.axes_list,
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
    assert dummy_nexus_file[module_nexus_path + "data_size"].dtype == np.uint32


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
    test_detector_spec = EigerDetector("eiger", [512, 1028], "Si", 10000, -1)
    test_detector_spec.constants["software_version"] = "0.0.0"

    write_NXcollection(nxdet, test_detector_spec, "images", 10)

    spec = "/entry/instrument/detector/detectorSpecific/"
    assert dummy_nexus_file[spec + "software_version"][()] == b"0.0.0"
    assert_array_equal(dummy_nexus_file[spec + "nimages"][()], 10)
    assert_array_equal(
        dummy_nexus_file[spec + "x_pixels"][()], test_detector_spec.image_size[1]
    )
    assert_array_equal(
        dummy_nexus_file[spec + "y_pixels"][()], test_detector_spec.image_size[0]
    )


def test_write_NXcollection_for_events(dummy_nexus_file):
    nxdet = dummy_nexus_file.require_group("/entry/instrument/detector")
    test_detector_spec = TristanDetector("Tristan 1M", [515, 2069])
    test_detector_spec.constants["software_version"] = "0.0.0"

    write_NXcollection(nxdet, test_detector_spec, ("events", None))

    spec = "/entry/instrument/detector/detectorSpecific/"
    assert dummy_nexus_file[spec + "software_version"][()] == b"0.0.0"
    assert_array_equal(
        dummy_nexus_file[spec + "timeslice_rollover_bits"][()],
        test_detector_spec.constants["timeslice_rollover"],
    )
    assert_array_equal(dummy_nexus_file[spec + "detector_tick"][()], 1562.5)
    assert dummy_nexus_file[spec + "detector_tick"].attrs["units"] == b"ps"
    assert dummy_nexus_file[spec + "detector_frequency"].attrs["units"] == b"Hz"


def test_write_NXdetector_for_eiger_images_without_meta_file(
    dummy_nexus_file, mock_eiger
):
    det = "/entry/instrument/detector/"

    write_NXdetector(
        dummy_nexus_file,
        mock_eiger,
        100,
    )

    # Check some general things
    params = mock_eiger.detector_params
    assert dummy_nexus_file[det + "description"][()] == params.description.encode()
    assert dummy_nexus_file[det + "type"][()] == params.detector_type.encode()

    assert_array_equal(
        dummy_nexus_file[det + "beam_center_x"][()], mock_eiger.beam_center[0]
    )
    assert dummy_nexus_file[det + "beam_center_y"].attrs["units"] == b"pixels"
    assert_array_equal(dummy_nexus_file[det + "y_pixel_size"], 7.5e-05)
    assert dummy_nexus_file[det + "x_pixel_size"].attrs["units"] == b"m"

    # Check no mask
    assert "pixel_mask" not in list(dummy_nexus_file[det].keys())

    # Check detector axis and distance
    tr = det + "transformations/"
    assert "det_z" in list(dummy_nexus_file[tr].keys())
    axis_entry = tr + "det_z"
    assert_array_equal(
        mock_eiger.detector_axes[0].start_pos, dummy_nexus_file[axis_entry][()]
    )
    assert dummy_nexus_file[axis_entry].attrs["depends_on"] == b"."
    assert dummy_nexus_file[axis_entry].attrs["transformation_type"] == b"translation"
    assert dummy_nexus_file[axis_entry].attrs["units"] == b"mm"
    assert_array_equal(
        dummy_nexus_file[axis_entry].attrs["vector"][()],
        mock_eiger.detector_axes[0].vector,
    )

    # Check that distance is in meters instead of mm
    assert_array_equal(
        dummy_nexus_file[det + "distance"], mock_eiger.detector_axes[0].start_pos / 1000
    )
    assert dummy_nexus_file[det + "distance"].attrs["units"] == b"m"

    # Check that detector_z has also been written in /detector
    assert "detector_z" in list(dummy_nexus_file[det].keys())
    assert "det_z" in list(dummy_nexus_file[det + "detector_z"].keys())


@patch("nexgen.nxs_write.nxclass_writers.write_NXcollection")
def test_write_NXdetector_for_eiger_images_with_meta_file(
    mock_nxcoll_writer,
    dummy_nexus_file,
    dummy_eiger_meta_file,
    mock_eiger,
):
    det = "/entry/instrument/detector/"

    write_NXdetector(
        dummy_nexus_file,
        mock_eiger,
        90,
        Path(dummy_eiger_meta_file.name),
    )
    assert "pixel_mask" in list(dummy_nexus_file[det].keys())
    assert "pixel_mask_applied" in list(dummy_nexus_file[det].keys())
    assert "flatfield" in list(dummy_nexus_file[det].keys())
    assert "bit_depth_readout" in list(dummy_nexus_file[det].keys())

    mock_nxcoll_writer.assert_called_once()


def test_write_NXinstrument(dummy_nexus_file, mock_source, mock_beam, mock_attenuator):
    instr = "/entry/instrument/"

    write_NXinstrument(
        dummy_nexus_file,
        mock_beam,
        mock_attenuator,
        mock_source,
    )

    assert "attenuator" in list(dummy_nexus_file[instr].keys())
    assert "beam" in list(dummy_nexus_file[instr].keys())
    assert dummy_nexus_file[instr + "name"][()] == b"DIAMOND BEAMLINE I03"
    assert dummy_nexus_file[instr + "name"].attrs["short_name"] == b"DLS I03"


def test_write_NXinstrument_sets_correct_instrument_name(
    dummy_nexus_file, mock_attenuator, mock_beam
):
    instr = "/entry/instrument/"

    mock_beam.wavelength = 0.001
    mock_attenuator.transmission = 1.0
    mock_electron_source = Source(
        "eBic",
        Facility(
            "Diamond Light Source", "DLS", "Electron Source", "DIAMOND MICROSCOPE"
        ),
        probe="electron",
    )

    write_NXinstrument(
        dummy_nexus_file,
        mock_beam,
        mock_attenuator,
        mock_electron_source,
        reset_instrument_name=True,
    )

    assert dummy_nexus_file[instr + "name"][()] == b"DIAMOND MICROSCOPE eBic"
    assert dummy_nexus_file[instr + "name"].attrs["short_name"] == b"DLS eBic"


def test_write_NXattenuator(dummy_nexus_file, mock_attenuator):
    nx_instrument = dummy_nexus_file.require_group("/entry/instrument")

    write_NXattenuator(nx_instrument, mock_attenuator)

    assert "attenuator" in list(dummy_nexus_file["/entry/instrument"].keys())
    assert "attenuator_transmission" in list(
        dummy_nexus_file["/entry/instrument/attenuator"].keys()
    )
    assert (
        dummy_nexus_file["/entry/instrument/attenuator/attenuator_transmission"][()]
        == 10.0
    )


def test_write_NXbeam_for_polychromatic_beam(dummy_nexus_file, mock_polychromatic_beam):
    beam_loc = "/entry/instrument/beam"
    nx_instrument = dummy_nexus_file.require_group("/entry/instrument")

    write_NXbeam(nx_instrument, mock_polychromatic_beam)

    assert "beam" in list(dummy_nexus_file["/entry/instrument"].keys())
    assert "incident_wavelength" in list(dummy_nexus_file[beam_loc].keys())
    assert "incident_wavelength_weights" in list(dummy_nexus_file[beam_loc].keys())
    assert "total_flux" in list(dummy_nexus_file[beam_loc].keys())
    assert_array_equal(
        dummy_nexus_file[f"{beam_loc}/incident_wavelength"][()], [0.6, 0.7]
    )
    assert_array_equal(
        dummy_nexus_file[f"{beam_loc}/incident_wavelength_weights"][()],
        mock_polychromatic_beam.wavelength_weights,
    )
    assert (
        dummy_nexus_file[f"{beam_loc}/total_flux"][()] == mock_polychromatic_beam.flux
    )


def test_write_NEbeam_for_polychromatic_beam_fails_if_wrong_number_of_weights(
    dummy_nexus_file, mock_polychromatic_beam
):
    mock_polychromatic_beam.wavelength_weights = [0.5]
    nx_instrument = dummy_nexus_file.require_group("/entry/instrument")

    with pytest.raises(ValueError):
        write_NXbeam(nx_instrument, mock_polychromatic_beam)
