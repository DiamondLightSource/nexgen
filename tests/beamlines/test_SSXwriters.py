from unittest.mock import patch

import pytest

from nexgen.beamlines.SSX_Eiger_nxs import ssx_eiger_writer


@patch("nexgen.beamlines.SSX_Eiger_nxs.ssx_collect")
def test_writer_fails_for_Wrong_expt_type(fake_ssx_collect):
    with pytest.raises(ValueError):
        ssx_eiger_writer(
            "/path/to/file",
            "somefile",
            "i24",
            1,
            expt_type="aaa",
        )


@patch("nexgen.beamlines.SSX_Eiger_nxs.ssx_collect")
@patch("nexgen.beamlines.SSX_Eiger_nxs.log")
def test_writer_fails_for_beamline_not_i24_or_i19(fake_log, fake_ssx):
    with pytest.raises(ValueError):
        ssx_eiger_writer(
            "/path/to/file",
            "somefile",
            "i23",
            1,
        )
