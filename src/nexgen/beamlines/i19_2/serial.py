import logging
from pathlib import Path
from typing import Any, Sequence

import h5py
from numpy.typing import DTypeLike

from nexgen import log
from nexgen.beamlines.i19_2.main_writer import standard_nexus_writer
from nexgen.tools.vds_tools.strided_mapping import write_strided_vds

logger = logging.getLogger("nexgen.beamlines.i19_2.serial")


def _setup_logging(wdir: Path):
    # Define a file handler
    logfile = wdir / "I19_2_nxs_writer.log"
    # Configure logging
    log.config(logfile.as_posix())


def serial_nexus_writer(
    params: dict[str, Any],
    master_file: Path,
    detector_params: dict[str, Any] | None = None,
    n_frames: int | None = None,
    notes: dict[str, Any] | None = None,
):
    """Entry point function to gather all parameters from the beamline and kick off the nexus writer for a
    serial experiment on I19-2.

    Args:
        params (dict[str, Any]): Dictionary representation of CollectionParams, the main collection parameters
            needed by any experiment and any detector.
        master_file (Path): Full path to the nexus file to be written.
        detector_params (dict[str, Any]): Dictionary representation of ExtraDetectorParams, a set of
            parameters needed to use the correct writer/vds for the Eiger detector. Not needed for Tristan.
            Defaults to None, if not passed for Eiger, the default (legacy) values will be used.
        n_frames (int | None, optional): Number of images for the nexus file. Only needed if different
            from the tot_num_images in the collection params. If passed, the VDS will only contain the
            number of frames specified here. Defaults to None.
        notes (dict[str, Any] | None, optional): Any additional information to be written as NXnote,
            passed as a dictionary of (key, value) pairs where key represents the dataset name and
            value its data. Defaults to None.
    """
    if not detector_params:
        logger.warning(
            "No specific detector params have been passed. Will default to legacy eiger settings."
        )

    logger.info(f"Start nexus file writer for {master_file}")
    standard_nexus_writer(params, detector_params, master_file, n_frames, notes)


# Until issues in nxs_copy are fixed, pydantic errors abound
def _get_metadata_from_og_nexus(
    og_nxs: Path, new_nxs: Path, og_vds_key: str = "/entry/data/data"
) -> tuple[Sequence[int], DTypeLike]:
    """Copy metadata from original nexus file, remove blocked vds and extract data shape and type."""
    with h5py.File(og_nxs, "r") as nxs_in, h5py.File(new_nxs, "w") as nxs_out:
        nxs_in.copy("entry", nxs_out)
        # Extract full data shape and stype
        full_data_shape = nxs_in[og_vds_key].shape
        data_type = nxs_in[og_vds_key].dtype
        # Delete og vds
        del nxs_out[og_vds_key]
    return full_data_shape, data_type


# Temporary new function to create separated vds files
def serial_nexus_writer_with_strided_vds(og_nxs: Path | str, vds_names: list[str]):
    """Utility function to create a new nexus file starting from a standard one.

    Uses the standard nexus file with a blocked VDS to create new nexus files with strided VDS.
    eg. In stream2 mode, the eiger detector is able to collect two delays points at the same time.
    One is after the pump source (excited state) and the other is a longer delay once the excited
    state has dissipated (ground state). This will be reflected in two nexus files, the first of which
    maps to the ES frames and the secodn to the GS frames.

    Args:
        og_nxs (Path | str): Original nexus file to get most of the metadata from.
        vds_names (list[str]): Names to append to the new nexus files with strided VDS.
            The length of this list also determines how many files should be written and
            thus the stride.
    """
    if isinstance(og_nxs, str):
        og_nxs = Path(og_nxs)
    try:
        stride = len(vds_names)
        logger.info(f"Will write {stride} new nexus files with the vds.")
        for n, name in enumerate(vds_names):
            start_index = n
            new_nxs = og_nxs.parent / f"{og_nxs.stem}_{name}{og_nxs.suffix}"
            # Start by copying the original file and deleting the VDS
            logger.debug("Copy metadata from OG nexus")
            full_data_shape, data_type = _get_metadata_from_og_nexus(og_nxs, new_nxs)
            logger.debug(
                f"New nexus file {new_nxs} created, will proceed to writing VDS"
            )

            with h5py.File(new_nxs, "r+") as nxs:
                write_strided_vds(nxs, full_data_shape, start_index, stride, data_type)
            logger.info(f"File {new_nxs} written successfully.")
    except Exception as e:
        logger.error("Failed to write new nexus and VDS files")
        logger.exception(e)
