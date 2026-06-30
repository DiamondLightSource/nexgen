import pytest

from nexgen.beamlines.i19_2.parameters import CollectionParams, DetectorName


@pytest.fixture
def dummy_eiger_collection_params():
    return CollectionParams(
        exposure_time=0.01,
        beam_center=(100, 200),
        wavelength=0.4,
        metafile="/path/to/somefile_meta.h5",
        detector_name=DetectorName.EIGER,
    )


# @pytest.fixture
# def dummy_eiger_settings()
