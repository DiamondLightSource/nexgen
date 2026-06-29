import logging
from pathlib import Path
from typing import Any

import h5py
from numpy.typing import ArrayLike, DTypeLike
from pydantic import BaseModel, field_validator

from nexgen.beamlines.beamline_utils import collection_summary_log
from nexgen.beamlines.i19_2.constants import I19_2_EIGER
from nexgen.beamlines.i19_2.parameters import CollectionParams
from nexgen.nxs_utils import NxObjectsComposite
from nexgen.nxs_utils.axes import Axis
from nexgen.nxs_utils.detector import Detector, EigerDetector, EigerStreamFormat
from nexgen.nxs_utils.goniometer import Goniometer
from nexgen.nxs_utils.sample import Sample
from nexgen.nxs_utils.scan_utils import calculate_scan_points, identify_osc_axis
from nexgen.nxs_utils.source import Attenuator, Beam, Source
from nexgen.nxs_write.nxmx_writer import NXmxFileWriter
from nexgen.tools.meta_reader import define_vds_data_type, update_axes_from_meta
from nexgen.tools.metafile import DectrisMetafile
from nexgen.tools.vds_tools import (
    VdsMapping,
    VdsSettings,
    define_vds_dtype_from_bit_depth,
)

logger = logging.getLogger("nexgen.beamlines.I19_2.eiger")


class EigerSettings(BaseModel):
    master_file: Path
    use_meta: bool = False
    bit_depth: int = 32
    data_entry_key: str = "data"
    stream_format: EigerStreamFormat = EigerStreamFormat.LEGACY

    @field_validator("master_file", mode="before")
    @classmethod
    def _parse_master(cls, master_file: str | Path) -> Path:
        if isinstance(master_file, str):
            return Path(master_file)
        return master_file


def _is_stills(scan: ArrayLike) -> bool:
    if all(scan == scan[0]):
        return True
    return False


def _check_meta_parameters(
    parameters: CollectionParams, use_meta: bool, n_frames: int | None
):
    if not use_meta:
        if not parameters.axes_pos or not parameters.det_pos:
            logger.error(
                """
                If not using the meta file, please pass the complete axis information for goniometer
                and/or detector.
                """
            )
            raise ValueError(
                "No meta file selected and missing at least one of axes_pos or det_pos from parameter model."
            )
        if not n_frames and parameters.tot_num_images is None:
            logger.error(
                """
                If not using the meta file, please make sure either the total number of images is passed \
                or the number of frames has been passed. These values could be the same for a standard \
                collection, or different if the vds needs to only point to part of the dataset.
                """
            )
            raise ValueError(
                "Neither total number of images nor number of frames have been passed to the model."
            )


def _get_info_from_legacy_metafile(
    parameters: CollectionParams,
    gonio_axes: list[Axis],
    det_axes: list[Axis],
    n_frames: int | None,
) -> tuple[DTypeLike, int]:
    logger.info("User requested to update metadata using meta file.")
    with h5py.File(parameters.metafile, "r", libver="latest", swmr=True) as mh:
        meta = DectrisMetafile(mh)
        parameters.tot_num_images = meta.get_full_number_of_images()
        logger.info(
            f"Total number of images for this collection found in meta file: {parameters.tot_num_images}."
        )
        if not n_frames:
            n_frames = parameters.tot_num_images
            logger.info(
                "No specific numnber of frames requested, VDS will contain the full dataset."
            )
        vds_dtype = define_vds_data_type(meta)
        update_axes_from_meta(
            meta, gonio_axes, osc_axis=parameters.scan_axis, use_config=True
        )
        update_axes_from_meta(meta, det_axes)
        # WARNING.det_z not in _dectris, but det_distance is. Getting that.

        logger.info(
            "Goniometer and detector axes positions have been updated with values from the meta file."
        )
        if not parameters.wavelength:
            logger.info(
                "Wavelength hasn't been passed by user. Looking for it in the meta file."
            )
            parameters.wavelength = meta.get_wavelength()
        if not parameters.beam_center:
            logger.info(
                "Beam center position has't been passed by user. Looking for it in the meta file."
            )
            parameters.beam_center = tuple(meta.get_beam_center())
    return vds_dtype, n_frames


def _define_scan_axis_and_oscillation(
    parameters: CollectionParams, gonio_axes: list[Axis], n_frames: int
) -> tuple[str, dict[str, ArrayLike]]:
    scan_axis = identify_osc_axis(gonio_axes, "phi")
    # Check that found scan_axis matches
    if scan_axis != parameters.scan_axis:
        logger.warning(
            f"Scan axis {scan_axis} found different from requested one {parameters.scan_axis}."
            f"Defaulting to {parameters.scan_axis}. If wrong please check meta file."
        )
        scan_axis = parameters.scan_axis
    scan_idx = [n for n, ax in enumerate(gonio_axes) if ax.name == scan_axis][0]
    gonio_axes[scan_idx].num_steps = n_frames
    oscillation = calculate_scan_points(
        gonio_axes[scan_idx],
        rotation=True,
        tot_num_imgs=n_frames,
    )
    return scan_axis, oscillation


def eiger_writer(
    parameters: CollectionParams,
    eiger_settings: EigerSettings,
    vds_offset: int = 0,
    vds_mapping: VdsMapping = VdsMapping.BLOCKED,  # This is the usual one
    n_frames: int | None = None,
    notes: dict[str, Any] | None = None,
):
    _check_meta_parameters(parameters, eiger_settings.use_meta, n_frames)

    source = Source("I19-2")

    # Define Eiger 4M params
    eiger_params = EigerDetector(
        "Eiger 2X 4M",
        (2162, 2068),
        "CdTe",
        50649,
        -1,
        stream=eiger_settings.stream_format,
    )

    # Define Goniometer axes
    gonio_axes = I19_2_EIGER.gonio
    # Define Detector axes
    det_axes = I19_2_EIGER.det_axes

    if (
        eiger_settings.use_meta
        and eiger_settings.stream_format != EigerStreamFormat.CBOR
    ):
        vds_dtype, n_frames = _get_info_from_legacy_metafile(
            parameters, gonio_axes, det_axes, n_frames
        )
    else:
        logger.info(
            "Not using meta file to update metadata, only the external links will be set up."
        )
        vds_dtype = define_vds_dtype_from_bit_depth(eiger_settings.bit_depth)
        # wavelength = parameters.wavelength
        # beam_center = parameters.beam_center
        # Update axes
        # Goniometer
        for gax in parameters.axes_pos:
            idx = [n for n, ax in enumerate(gonio_axes) if ax.name == gax.id][0]
            gonio_axes[idx].start_pos = gax.start
            if gax.inc != 0.0:
                gonio_axes[idx].increment = gax.inc

        # Detector
        for dax in parameters.det_pos:
            idx = [n for n, ax in enumerate(det_axes) if ax.name == dax.id][0]
            det_axes[idx].start_pos = dax.start

        logger.info(
            "Goniometer and detector axes positions have been updated with values passed by the user."
        )

        # THIS IS AWFUL TO FIX LATER
        if not n_frames:
            n_frames = parameters.tot_num_images
        if not parameters.tot_num_images:
            parameters.tot_num_images = n_frames
            logger.warning(
                """
                As the total number of images was not set in the collection parameters, it has been set to \
                the requested number of frames.
                """
            )

    # Define beam and attenuator
    attenuator = Attenuator(parameters.transmission)
    beam = Beam(parameters.wavelength)

    # Scan
    scan_axis, oscillation = _define_scan_axis_and_oscillation(
        parameters, gonio_axes, n_frames
    )

    # Define Detector
    detector = Detector(
        eiger_params,
        det_axes,
        parameters.beam_center,
        parameters.exposure_time,
        [I19_2_EIGER.fast_axis, I19_2_EIGER.slow_axis],
    )

    # Define Goniometer
    goniometer = Goniometer(gonio_axes, oscillation)

    # Define Sample if needed
    sample = None
    if _is_stills(oscillation[scan_axis]):
        logger.info(f"Scan on axis {scan_axis} is actually a collection of stills")
        logger.debug(f"Will set sample depends_on to {scan_axis}")
        sample = Sample(depends_on=scan_axis)

    nx_objects = NxObjectsComposite(
        goniometer, detector, source, beam, attenuator, sample
    )

    collection_summary_log(
        logger,
        goniometer,
        detector,
        attenuator,
        beam,
        source,
        parameters.timestamps,
    )

    vds_settings = VdsSettings(
        vds_dtype,
        (n_frames, *detector.detector_params.image_size),
        vds_offset,
        vds_mapping,
    )

    start_writer(parameters, eiger_settings, nx_objects, vds_settings, notes)


def start_writer(
    parameters: CollectionParams,
    eiger_settings: EigerSettings,
    nx_objects: NxObjectsComposite,
    vds_settings: VdsSettings,
    notes: dict[str, Any] | None = None,
):
    # Write
    try:
        image_filename = parameters.metafile.as_posix().replace("_meta.h5", "")
        NXmx_writer = NXmxFileWriter(
            eiger_settings.master_file,
            nx_objects.goniometer,
            nx_objects.detector,
            nx_objects.source,
            nx_objects.beam,
            nx_objects.attenuator,
            parameters.tot_num_images,
            nx_objects.sample,
        )
        NXmx_writer.write(
            image_filename=image_filename,
            start_time=parameters.timestamps[0],
            data_entry_key=eiger_settings.data_entry_key,
        )
        NXmx_writer.write_vds(
            vds_offset=vds_settings.vds_offset,
            vds_shape=vds_settings.vds_shape,
            vds_dtype=vds_settings.vds_dtype,
        )  # TODO add mapping
        if parameters.timestamps[1]:
            NXmx_writer.update_timestamps(parameters.timestamps[1], "end_time")
        if notes:
            NXmx_writer.add_NXnote(notes)
        logger.info(f"The file {eiger_settings.master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {eiger_settings.master_file} couldn't be written correctly."
        )
        raise
