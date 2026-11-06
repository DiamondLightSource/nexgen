"""A writer to be used from GDA, usually only called from a command
line tool or a REST call.
"""

import logging

from nexgen.beamlines.GDAtools.ExtendedRequest import (
    ExtendedRequestIO,
    read_det_position_from_xml,
    read_scan_from_xml,
)
from nexgen.beamlines.i19_2.eiger import EigerSettings, eiger_writer
from nexgen.beamlines.i19_2.parameters import (
    CollectionParams,
    DetAxisPosition,
    DetectorName,
    ExtraDetectorParams,
    GonioAxisPosition,
    ParamsFromGDA,
)
from nexgen.beamlines.i19_2.tristan import tristan_writer
from nexgen.log import closes_logfile, setup_logging
from nexgen.utils import get_nexus_filename

logger = logging.getLogger("nexgen.beamlines.i19_2.from_gda")


def _get_params_from_ecr(parameters: ParamsFromGDA) -> CollectionParams:
    ecr = ExtendedRequestIO(parameters.xmlfile)
    logger.info("Read xml file and extract collection params")

    scan_axis, ax_pos, n_frames = read_scan_from_xml(ecr)

    axes_positions = [GonioAxisPosition(k, v[0], v[2], v[1]) for k, v in ax_pos.items()]

    det_pos = read_det_position_from_xml(ecr, parameters.detector_name.value)
    det_positions = [
        DetAxisPosition("two_theta", det_pos[0]),
        DetAxisPosition("det_z", det_pos[1]),
    ]

    params = CollectionParams(
        exposure_time=parameters.exposure_time,
        wavelength=parameters.wavelength,
        transmission=ecr.getTransmission(),
        beam_center=parameters.beam_center,
        metafile=parameters.metafile,
        detector_name=parameters.detector_name,
        tot_num_images=n_frames,
        scan_axis=scan_axis,
        axes_pos=axes_positions,
        det_pos=det_positions,
        timestamps=parameters.timestamps,
    )
    return params


@closes_logfile
def gda_nexus_writer(parameters: ParamsFromGDA):
    """Main entry point for the writer called by GDA scripts.

    Args:
        parameters (ParamsFromGDA): Parameter representation of all
            the information that can be gathere from GDA.
    """
    setup_logging(
        parameters.metafile.parent,
        f"gda_nxs_{parameters.detector_name.value}_writer.log",
    )

    logger.info("NeXus file writer for beamline I19-2 at DLS.")
    logger.info(
        f"Detector in use for this experiment: {parameters.detector_name.value}."
    )
    logger.info(f"Current collection directory: {parameters.metafile.parent}")

    collection_parameters = _get_params_from_ecr(parameters)

    master_file = get_nexus_filename(parameters.metafile)

    logger.info("NeXus file will be saved as %s" % master_file)

    match collection_parameters.detector_name:
        case DetectorName.EIGER:
            det_params = (
                ExtraDetectorParams(**parameters.detector_params)
                if parameters.detector_params
                else ExtraDetectorParams()
            )
            eiger_settings = EigerSettings(
                master_file=master_file,
                use_meta=det_params.use_meta,
                bit_depth=det_params.bit_depth,
                data_entry_key=det_params.data_entry_key,
                stream_format=det_params.stream_format,
            )
            logger.info("Kick off eiger writer")
            eiger_writer(
                collection_parameters,
                eiger_settings,
                det_params.vds_offset,
                det_params.vds_mapping,
            )
        case DetectorName.TRISTAN:
            logger.info("Kick off tristan writer")
            tristan_writer(
                collection_parameters,
                master_file,
            )
