from datetime import datetime
from unittest.mock import patch

import numpy as np

from nexgen.nxs_utils import Axis, Goniometer, TransformationType

fake_gonio = Goniometer(
    [Axis("omega", ".", TransformationType.ROTATION, (0, 0, -1), 0.0)],
    {"omega": np.arange(0, 10, 1)},
)


@patch("nexgen.nxs_write.nxmx_writer.write_NXsample")
@patch("nexgen.nxs_write.nxmx_writer.write_NXsource")
@patch("nexgen.nxs_write.nxmx_writer.write_NXdetector_module")
@patch("nexgen.nxs_write.nxmx_writer.write_NXdetector")
@patch("nexgen.nxs_write.nxmx_writer.write_NXinstrument")
@patch("nexgen.nxs_write.nxmx_writer.write_NXdata")
@patch("nexgen.nxs_write.nxmx_writer.write_NXentry")
def test_NXmxFileWriter_write(
    mock_NXentry,
    mock_NXdata,
    mock_NXinstrument,
    mock_NXdetector,
    mock_NXmodule,
    mock_NXsource,
    mock_NXsample,
    dummy_NXmxWriter,
):
    dummy_NXmxWriter.goniometer = fake_gonio
    dummy_NXmxWriter.write(write_mode="w")
    mock_NXentry.assert_called_once()
    mock_NXdata.assert_called_once()
    mock_NXinstrument.assert_called_once()
    mock_NXdetector.assert_called_once()
    mock_NXmodule.assert_called_once()
    mock_NXsource.assert_called_once()
    mock_NXsample.assert_called_once()


@patch("nexgen.nxs_write.nxmx_writer.write_NXdatetime")
def test_NXmxFileWriter_updates_timestamps(mock_NXdatetime, dummy_NXmxWriter):
    fake_timestap = datetime.now()
    dummy_NXmxWriter.update_timestamps(fake_timestap, "start_time")
    mock_NXdatetime.assert_called_once()


@patch("nexgen.nxs_write.nxmx_writer.write_NXnote")
def test_NXmxFileWriter_adds_note(mock_NXnote, dummy_NXmxWriter):
    fake_notes = {"foo": "bar"}
    dummy_NXmxWriter.add_NXnote(fake_notes)
    mock_NXnote.assert_called_once()


@patch("nexgen.nxs_write.nxmx_writer.image_vds_writer")
def test_NXmxFileWriter_write_vds(mock_vds_writer, dummy_NXmxWriter):
    dummy_NXmxWriter.goniometer = fake_gonio
    dummy_NXmxWriter.detector.detector_params.image_size = (100, 100)
    dummy_NXmxWriter.write_vds()
    mock_vds_writer.assert_called_once()
