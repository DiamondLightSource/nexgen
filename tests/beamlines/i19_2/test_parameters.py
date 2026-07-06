from pathlib import Path

from nexgen.beamlines.i19_2.parameters import CollectionParams


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
    assert params.timestamps[1] == ""
