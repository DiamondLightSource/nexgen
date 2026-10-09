from pathlib import Path

from nexgen.beamlines.i19_2.parameters import (
    CollectionParams,
    DetectorName,
    ParamsFromGDA,
)


def test_collection_parameters(dummy_eiger_collection_params: CollectionParams):
    dummy_eiger_collection_params.tot_num_images = 10
    assert isinstance(dummy_eiger_collection_params.metafile, Path)
    assert not dummy_eiger_collection_params.axes_pos
    assert not dummy_eiger_collection_params.det_pos
    assert dummy_eiger_collection_params.tot_num_images == 10


def test_collection_parameters_timestamps():
    params = CollectionParams(
        exposure_time=0.01,
        beam_center=(100, 200),
        wavelength=0.4,
        metafile="/path/to/somefile_meta.h5",
        detector_name="eiger",
        timestamps=("2026-07-06 17:00:21", None),
    )

    assert params.timestamps[0] == "2026-07-06T17:00:21Z"
    assert params.timestamps[1] is None


def test_parameters_tristan_from_GDA():
    params = ParamsFromGDA(
        metafile="/path/to/file_01_meta.h5",
        xmlfile="/tmp/ecr_file.xml",
        detector_name="tristan",
        exposure_time=0.02,
        beam_center=(2345, 1678),
        wavelength=0.69,
    )
    assert isinstance(params.metafile, Path)
    assert isinstance(params.metafile, Path)
    assert params.detector_name == DetectorName.TRISTAN
    assert params.timestamps == (None, None)
    assert not params.detector_params


def test_parameters_eiger_from_GDA():
    params = ParamsFromGDA(
        metafile="/path/to/file_01_meta.h5",
        xmlfile="/tmp/ecr_file.xml",
        detector_name="eiger",
        exposure_time=0.02,
        beam_center=(2345, 1678),
        wavelength=0.69,
        detector_params={"bit_depth": 16},
    )

    assert params.detector_name == DetectorName.EIGER
    assert params.detector_params["bit_depth"] == 16
