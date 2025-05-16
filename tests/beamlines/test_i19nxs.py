from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from nexgen.beamlines.I19_2_nxs import (
    CollectionParams,
    ExperimentTypeError,
    eiger_writer,
    nexus_writer,
)


def test_nexus_writer_raises_error_for_serial():
    with pytest.raises(ExperimentTypeError):
        nexus_writer("/path/to/meta", "eiger", 0.1, serial=True)


@patch("nexgen.beamlines.I19_2_nxs.log")
def test_nexus_writer_fails_if_missing_n_imgs_and_not_using_meta(fake_log):
    with pytest.raises(ValueError):
        nexus_writer("/path/to/meta", "eiger", 0.1, use_meta=False)


def test_eiger_nxs_writer_fails_if_missing_axes_and_no_meta():
    fake_params = CollectionParams(
        exposure_time=0.01,
        beam_center=(100, 200),
        wavelength=0.4,
        metafile="somefile",
        detector_name="eiger",
    )
    with pytest.raises(ValueError):
        eiger_writer(Path("/path/to/meta"), fake_params, use_meta=False)
