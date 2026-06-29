import logging
from pathlib import Path
from typing import Any

from nexgen import log
from nexgen.beamlines.i19_2.constants import DEFAULT_DATA_KEY
from nexgen.beamlines.i19_2.eiger import EigerSettings, eiger_writer
from nexgen.beamlines.i19_2.parameters import CollectionParams, DetectorName
from nexgen.nxs_utils.detector import EigerStreamFormat
from nexgen.tools.vds_tools import VdsMapping
from nexgen.utils import get_iso_timestamp

logger = logging.getLogger("nexgen.beamlines.i19_2.serial")


def _setup_logging(wdir: Path):
    # Define a file handler
    logfile = wdir / "I19_2_nxs_writer.log"
    # Configure logging
    log.config(logfile.as_posix())


def serial_nexus_writer(
    params: dict[str, Any],
    master_file: Path,
    use_meta: bool = False,
    vds_offset: int = 0,
    n_frames: int | None = None,
    bit_depth: int = 32,
    data_entry_key: str = DEFAULT_DATA_KEY,
    eiger_stream_format: EigerStreamFormat = EigerStreamFormat.LEGACY,
    vds_mapping: VdsMapping = VdsMapping.BLOCKED,
    notes: dict[str, Any] | None = None,
):
    _setup_logging(master_file.parent)

    collection_params = CollectionParams(**params)
    logger.info("NeXus file writer for beamline I19-2 at DLS.")
    logger.info(
        f"Detector in use for this experiment: {collection_params.detector_name.value}."
    )
    logger.info(f"Current collection directory: {collection_params.metafile.parent}")

    # Get NeXus filename
    logger.info("NeXus file will be saved as %s" % master_file)

    # Get timestamps in the correct format if they aren't already
    # Should be passed as a string instead of datetime from ui .strftime("%Y-%m-%dT%H:%M:%S")
    timestamps = (
        get_iso_timestamp(collection_params.timestamps[0]),
        get_iso_timestamp(collection_params.timestamps[1]),
    )
    collection_params.timestamps = timestamps

    match collection_params.detector_name:
        case DetectorName.EIGER:
            eiger_settings = EigerSettings(
                master_file, use_meta, bit_depth, data_entry_key, eiger_stream_format
            )
            eiger_writer(
                collection_params,
                eiger_settings,
                vds_offset,
                vds_mapping,
                n_frames,
                notes,
            )
        case DetectorName.TRISTAN:
            logger.error("TRISTAN NOT IMPLEMENTED YET!")
