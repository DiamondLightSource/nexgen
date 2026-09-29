import logging
from pathlib import Path
from typing import Any

from nexgen.beamlines.beamline_utils import collection_summary_log
from nexgen.beamlines.i19_2.constants import I19_2_SOURCE, I19_2_TRISTAN
from nexgen.beamlines.i19_2.parameters import CollectionParams
from nexgen.nxs_utils import NxObjectsComposite
from nexgen.nxs_utils.detector import Detector, TristanDetector
from nexgen.nxs_utils.goniometer import Goniometer
from nexgen.nxs_utils.sample import Sample
from nexgen.nxs_utils.scan_utils import is_stills
from nexgen.nxs_utils.source import Attenuator, Beam
from nexgen.nxs_write.nxmx_writer import EventNXmxFileWriter

logger = logging.getLogger("nexgen.beamlines.I19_2.tristan")


def _get_master_file_name(meta_file: Path) -> Path:
    return meta_file.parent / meta_file.name.replace("_meta.h5", ".nxs")


def tristan_writer(
    parameters: CollectionParams,
    master_file: Path | str | None = None,
    notes: dict[str, Any] | None = None,
):
    source = I19_2_SOURCE

    # Define Tristan 10M params
    tristan_params = TristanDetector("Tristan 10M", (3043, 4183))

    # Define beam and attenuator
    attenuator = Attenuator(parameters.transmission)
    beam = Beam(parameters.wavelength)

    # Define Goniometer axes
    gonio_axes = I19_2_TRISTAN.gonio
    # Define Detector axes
    det_axes = I19_2_TRISTAN.det_axes

    # Update axes
    # Goniometer
    for gax in parameters.axes_pos:
        idx = [n for n, ax in enumerate(gonio_axes) if ax.name == gax.id][0]
        gonio_axes[idx].start_pos = gax.start
    # Detector
    for dax in parameters.det_pos:
        idx = [n for n, ax in enumerate(det_axes) if ax.name == dax.id][0]
        det_axes[idx].start_pos = dax.start

    # Scan
    scan_axis = parameters.scan_axis if parameters.scan_axis else "phi"
    scan_idx = [n for n, ax in enumerate(gonio_axes) if ax.name == scan_axis][0]
    oscillation = {
        scan_axis: (gonio_axes[scan_idx].start_pos, gonio_axes[scan_idx].end_pos)
    }

    # Define Goniometer
    goniometer = Goniometer(gonio_axes, oscillation)
    # Define Detector
    detector = Detector(
        tristan_params,
        det_axes,
        parameters.beam_center,
        parameters.exposure_time,
        [I19_2_TRISTAN.fast_axis, I19_2_TRISTAN.slow_axis],
    )

    # Define Sample if needed
    sample = None
    if is_stills(oscillation[scan_axis]):
        logger.info(f"Scan on axis {scan_axis} is actually a collection of stills")
        logger.debug(f"Will set sample depends_on to {scan_axis}")
        sample = Sample(depends_on=scan_axis)

    nx_objects = NxObjectsComposite(
        goniometer=goniometer,
        detector=detector,
        source=source,
        beam=beam,
        attenuator=attenuator,
        sample=sample,
    )

    collection_summary_log(
        logger,
        gonio_axes,
        detector,
        attenuator,
        beam,
        source,
        parameters.timestamps,
    )

    # Master file name
    if not master_file:
        master_file = _get_master_file_name(parameters.metafile)

    if isinstance(master_file, str):
        master_file = Path(master_file)

    start_writer(parameters, nx_objects, master_file, notes)


def start_writer(
    parameters: CollectionParams,
    nx_objects: NxObjectsComposite,
    master_file: Path,
    notes: dict[str, Any] | None = None,
):
    # Write
    try:
        image_filename = parameters.metafile.stem.replace("_meta", "")
        NXmx_tristan_writer = EventNXmxFileWriter(
            master_file,
            nx_objects.goniometer,
            nx_objects.detector,
            nx_objects.source,
            nx_objects.beam,
            nx_objects.attenuator,
            sample=nx_objects.sample,
        )
        NXmx_tristan_writer.write(
            image_filename=image_filename,
            start_time=parameters.timestamps[0],
        )
        if parameters.timestamps[1]:
            NXmx_tristan_writer.update_timestamps(parameters.timestamps[1], "end_time")
        if notes:
            NXmx_tristan_writer.add_NXnote(notes)
        logger.info(f"The file {master_file} was written correctly.")
    except Exception as err:
        logger.exception(err)
        logger.info(
            f"An error occurred and {master_file} couldn't be written correctly."
        )
        raise
