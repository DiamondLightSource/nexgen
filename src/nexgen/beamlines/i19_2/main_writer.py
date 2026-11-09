import logging
from pathlib import Path
from typing import Any

from nexgen.beamlines.i19_2.eiger import EigerSettings, eiger_writer
from nexgen.beamlines.i19_2.parameters import (
    CollectionParams,
    DetectorName,
    ExtraDetectorParams,
)
from nexgen.beamlines.i19_2.tristan import tristan_writer
from nexgen.log import closes_logfile, setup_logging
from nexgen.utils import get_nexus_filename

logger = logging.getLogger("nexgen.beamlines.i19_2.main_writer")


def main_writer_i19(
    collection_parameters: CollectionParams,
    extra_detector_params: ExtraDetectorParams | None = None,
    master_file: Path | None = None,
    n_frames: int | None = None,
    notes: dict[str, Any] | None = None,
):
    """Entry point function to gather all parameters from the beamline and kick off the nexus writer for a
    any experiment on I19-2. The serial writer refers to this after a few checks have been run on its non
    optional fields.

    Args:
        params (CollectionParams): Dictionary representation of CollectionParams, the main collection parameters
            needed by any experiment and any detector.
        extra_detector_params (ExtraDetectorParams | None, optional): Dictionary representation of ExtraDetectorParams, a set of
            parameters needed to use the correct writer/vds for the Eiger detector. Not needed for Tristan.
            Defaults to None, if not passed for Eiger, the default (legacy) values will be used.
        master_file (Path): Full path to the nexus file to be written. For a standard collection it could
            be None, as the filename can be deduced from the meta file. Defaults to None.
        n_frames (int | None, optional): Number of images for the nexus file. Only needed if different
            from the tot_num_images in the collection params. If passed, the VDS will only contain the
            number of frames specified here. Defaults to None.
        notes (dict[str, Any] | None, optional): Any additional information to be written as NXnote,
            passed as a dictionary of (key, value) pairs where key represents the dataset name and
            value its data. Defaults to None.
    """
    logger.info("NeXus file writer for beamline I19-2 at DLS.")
    logger.info(
        f"Detector in use for this experiment: {collection_parameters.detector_name.value}."
    )
    logger.info(
        f"Current collection directory: {collection_parameters.metafile.parent}"
    )

    # Get NeXus filename
    if not master_file:
        master_file = get_nexus_filename(collection_parameters.metafile)
    logger.info("NeXus file will be saved as %s" % master_file)

    match collection_parameters.detector_name:
        case DetectorName.EIGER:
            eiger_settings = EigerSettings(
                master_file=master_file,
                use_meta=extra_detector_params.use_meta,
                bit_depth=extra_detector_params.bit_depth,
                data_entry_key=extra_detector_params.data_entry_key,
                stream_format=extra_detector_params.stream_format,
            )
            logger.info("Kick off eiger writer")
            eiger_writer(
                collection_parameters,
                eiger_settings,
                extra_detector_params.vds_offset,
                extra_detector_params.vds_mapping,
                n_frames,
                notes,
            )
        case DetectorName.TRISTAN:
            logger.info("Kick off tristan writer")
            tristan_writer(
                collection_parameters,
                master_file,
                notes,
            )


@closes_logfile
def basic_nxmx_writer(
    params: dict[str, Any],
    detector_params: dict[str, Any] | None = None,
):
    """Entry point with logging to create a basic nxmx format file for i19-2."""
    collection_parameters = CollectionParams(**params)
    setup_logging(collection_parameters.metafile.parent)
    detector_parameters = (
        ExtraDetectorParams(**detector_params)
        if detector_params
        else ExtraDetectorParams()
    )
    main_writer_i19(collection_parameters, detector_parameters)
