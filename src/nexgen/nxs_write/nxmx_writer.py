"""
A writer for NXmx format NeXus Files.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np
from numpy.typing import DTypeLike

from ..nxs_utils.detector import Detector
from ..nxs_utils.goniometer import Goniometer
from ..nxs_utils.source import Attenuator, Beam, Source
from ..tools.vds_tools import (
    clean_unused_links,
    image_vds_writer,
    jungfrau_vds_writer,
)
from ..utils import (
    MAX_FRAMES_PER_DATASET,
    MAX_SUFFIX_DIGITS,
    get_filename_template,
)
from .nxclass_writers import (
    write_NXdata,
    write_NXdatetime,
    write_NXdetector,
    write_NXdetector_module,
    write_NXentry,
    write_NXinstrument,
    write_NXnote,
    write_NXsample,
    write_NXsource,
)
from .write_utils import TSdset, calculate_estimated_end_time

# Logger
nxmx_logger = logging.getLogger("nexgen.NXmxFileWriter")
nxmx_logger.setLevel(logging.DEBUG)


class NXmxFileWriter:
    """A class to generate NXmx format NeXus files."""

    def __init__(
        self,
        filename: Path | str,
        goniometer: Goniometer,
        detector: Detector,
        source: Source,
        beam: Beam,
        attenuator: Attenuator,
        tot_num_imgs: int,  # | None = None,
    ):
        self.filename = Path(filename).expanduser().resolve()
        self.goniometer = goniometer
        self.detector = detector
        self.source = source
        self.beam = beam
        self.attenuator = attenuator
        self.tot_num_imgs = tot_num_imgs

    def _get_meta_file(self, image_filename: str = None) -> Path | None:
        """Get filename_meta.h5 file in directory if it's supposed to exist."""
        if self.detector.detector_params.hasMeta is False:
            nxmx_logger.debug("No meta file for this collection.")
            return None
        if image_filename:
            return self.filename.parent / f"{image_filename}_meta.h5"
        else:
            return self.filename.parent / f"{self.filename.stem}_meta.h5"

    def _get_collection_time(self) -> float:
        """_Returns total collection time."""
        return self.detector.exp_time * self.tot_num_imgs

    def _get_data_files_list(
        self,
        image_filename: str | None = None,
    ) -> list[Path]:
        """Get list of datafiles.

        Args:
            image_filename (str | None, optional): Filename stem to use to look for image files. Needed in case it doesn't match \
                the NeXus file name. Defaults to None.

        Returns:
            list[Path]: List of data files to link to.
        """
        num_files = math.ceil(self.tot_num_imgs / MAX_FRAMES_PER_DATASET)
        template = (
            get_filename_template(self.filename)
            if not image_filename
            else (
                self.filename.parent / f"{image_filename}_%0{MAX_SUFFIX_DIGITS}d.h5"
            ).as_posix()
        )
        datafiles = [Path(template % i) for i in range(1, num_files + 1)]
        nxmx_logger.debug(f"Number of datafiles to be written: {len(datafiles)}.")
        return datafiles

    def update_timestamps(
        self, timestamp: datetime | str, dset_name: TSdset = "end_time"
    ):
        """Save timestamps for start and/or end collection if not written before.

        Args:
            timestamp (datetime | str): Timestamp, as datetime or str.
            dset_name (TSdset, optional): Name of dataset to write to nexus file.\
                Allowed values: ["start_time", "end_time", "end_time_estimated". Defaults to "end_time".
        """
        with h5py.File(self.filename, "r+") as nxs:
            write_NXdatetime(nxs, timestamp, dset_name)
        nxmx_logger.info(f"{dset_name} timestamp for collection updated.")

    def add_NXnote(self, notes: dict, loc: str = "/entry/notes"):
        """Save any additional information as NXnote at the end of the collection.

        Args:
            notes (dict): Dictionary of (key, value) pairs where key represents the \
                dataset name and value its data.
            loc (str, optional): Location in the NeXus file to save metadata. \
                Defaults to "/entry/notes".
        """
        with h5py.File(self.filename, "r+") as nxs:
            write_NXnote(nxs, loc, notes)
        nxmx_logger.debug(f"Notes saved in {loc}.")

    def write(
        self,
        image_datafiles: list | None = None,
        image_filename: str | None = None,
        start_time: datetime | str | None = None,
        est_end_time: datetime | str | None = None,
        write_mode: str = "x",
        add_non_standard: bool = True,
    ):
        """Write the NXmx format NeXus file.

        This function calls the writers for the main NXclass objects.

        Args:
            image_datafiles (list | None, optional): List of image data files. If not passed, \
                the program will look for files with the stem_######.h5 in the target directory. \
                Defaults to None.
            image_filename (str | None, optional): Filename stem to use to look for image files. \
                Needed in case it doesn't match the NeXus file name. Format: filename_runnumber. \
                Defaults to None.
            start_time (datetime | str, optional): Collection start time if available, in the \
                format "%Y-%m-%dT%H:%M:%SZ".Defaults to None.
            est_end_time (datetime | str, optional): Collection estimated end time if available, \
                in the format "%Y-%m-%dT%H:%M:%SZ". Defaults to None.
            write_mode (str, optional): String indicating writing mode for the output NeXus file. \
                Accepts any valid h5py file opening mode. Defaults to "x".
            add_non_standard (bool, optional): Flag if non-standard NXsample fields should be added \
                for processing to work. Defaults to True, will change in the future.
        """
        metafile = self._get_meta_file(image_filename)
        if metafile:
            nxmx_logger.debug(f"Metafile name: {metafile.as_posix()}.")

        datafiles = (
            image_datafiles
            if image_datafiles
            else self._get_data_files_list(image_filename)
        )

        module = self.detector.get_module_info()

        osc, transl = self.goniometer.define_scan_from_goniometer_axes()

        with h5py.File(self.filename, write_mode) as nxs:
            # NXentry and NXmx definition
            write_NXentry(nxs)

            # Start and estimated end time if known
            if start_time:
                write_NXdatetime(nxs, start_time, "start_time")
                if not est_end_time:
                    tot_exp_time = self._get_collection_time()
                    est_end = calculate_estimated_end_time(start_time, tot_exp_time)
                    write_NXdatetime(nxs, est_end, "end_time_estimated")
            if est_end_time:
                write_NXdatetime(nxs, est_end_time, "end_time_estimated")

            # NXdata: entry/data
            write_NXdata(
                nxs,
                datafiles,
                "images",
                list(osc.keys())[0],
            )

            # NXinstrument: entry/instrument
            write_NXinstrument(
                nxs,
                self.beam,
                self.attenuator,
                self.source,
            )

            # NXdetector: entry/instrument/detector
            write_NXdetector(
                nxs,
                self.detector,
                self.tot_num_imgs,
                metafile,
            )

            # NXmodule: entry/instrument/detector/module
            write_NXdetector_module(
                nxs,
                module,
                self.detector.detector_params.image_size,
                self.detector.detector_params.pixel_size,
                beam_center=self.detector.beam_center,
            )

            # NXsource: entry/source
            write_NXsource(nxs, self.source)

            # NXsample: entry/sample
            write_NXsample(
                nxs,
                self.goniometer.axes_list,
                "images",
                osc,
                transl,
                sample_depends_on=None,  # TODO
                add_nonstandard_fields=add_non_standard,
            )

    def write_vds(
        self,
        vds_offset: int = 0,
        vds_shape: tuple[int, int, int] = None,
        vds_dtype: DTypeLike = np.uint16,
        clean_up: bool = False,
    ):
        """Write a Virtual Dataset.

        This method adds a VDS under /entry/data/data in the NeXus file, linking to either the full datasets or the subset defined by \
        vds_offset (used as start index) and vds_shape.
        WARNING. Only use clean up if the data collection is finished and all the files have already been written.

        Args:
            vds_offset (int, optional): Start index for the vds writer. Defaults to 0.
            vds_shape (tuple[int,int,int], optional): Shape of the data which will be linked in the VDS. If not passed, it will be defined as \
            (tot_num_imgs - start_idx, *image_size). Defaults to None.
            vds_dtype (DTypeLike, optional): The type of the input data. Defaults to np.uint16.
            clean_up(bool, optional): Clean up unused links in vds. Defaults to False.
        """
        if not vds_shape:
            vds_shape = (
                self.tot_num_imgs - vds_offset,
                *self.detector.detector_params.image_size,
            )
            if self.goniometer.get_number_of_scan_points() != vds_shape[0]:
                vds_shape = (
                    self.goniometer.get_number_of_scan_points(),
                    *vds_shape[1:],
                )
                nxmx_logger.warning(
                    "The number of scan points doesn't match the calculated vds_shape. \
                    Resetting it to match the number of frames indicated by the scan."
                )

        nxmx_logger.debug(f"VDS shape set to {vds_shape}.")

        with h5py.File(self.filename, "r+") as nxs:
            if "jungfrau" in self.detector.detector_params.description.lower():
                jungfrau_vds_writer(
                    nxs,
                    (self.tot_num_imgs, *self.detector.detector_params.image_size),
                    data_type=vds_dtype,
                )
            else:
                image_vds_writer(
                    nxs,
                    (self.tot_num_imgs, *self.detector.detector_params.image_size),
                    start_index=vds_offset,
                    vds_shape=vds_shape,
                    data_type=vds_dtype,
                )
            if clean_up is True:
                nxmx_logger.warning("Starting clean up of unused links.")
                clean_unused_links(
                    nxs,
                    vds_shape=vds_shape,
                    start_index=vds_offset,
                )

            # If number of frames in the VDS is lower than the total, nimages in NXcollection should be overwritten to match this
            if vds_shape[0] < self.tot_num_imgs:
                del nxs["/entry/instrument/detector/detectorSpecific/nimages"]
                nxs["/entry/instrument/detector/detectorSpecific"].create_dataset(
                    "nimages", data=vds_shape[0]
                )


class EventNXmxFileWriter(NXmxFileWriter):
    """A class to generate NXmx-like NeXus files for event mode data."""

    def __init__(
        self,
        filename: Path | str,
        goniometer: Goniometer,
        detector: Detector,
        source: Source,
        beam: Beam,
        attenuator: Attenuator,
        axis_end_position: float | None = None,
    ):
        super().__init__(
            filename,
            goniometer,
            detector,
            source,
            beam,
            attenuator,
            None,
        )
        self.end_pos = axis_end_position

    def write(
        self,
        image_filename: str | None = None,
        start_time: datetime | str | None = None,
        write_mode: str = "x",
        add_non_standard: bool = False,
    ):
        """Write a NXmx-like NeXus file for event mode data collections.

        This method overrides the write() method of NXmxFileWriter, from which thsi class inherits.

        Args:
            start_time (datetime | str, optional): Collection estimated end time if available, in the \
                format "%Y-%m-%dT%H:%M:%SZ". Defaults to None.
            image_filename (str | None, optional): Filename stem to use to look for image files. \
                Needed in case it doesn't match the NeXus file name. Format: filename_runnumber. \
                Defaults to None.
            write_mode (str, optional): String indicating writing mode for the output NeXus file. \
                Accepts any valid h5py file opening mode. Defaults to "x".
            add_non_standard (bool, optional): Flag if non-standard NXsample fields should be added \
                for processing to work. Defaults to False.
        """
        # Get metafile
        # No data files, just link to meta
        metafile = super()._get_meta_file(image_filename=image_filename)

        module = self.detector.get_module_info()

        # Get scan info
        # Here no scan, just get (start, stop) from omega/phi as osc and None as transl
        osc, _ = self.goniometer.define_scan_axes_for_event_mode(self.end_pos)

        with h5py.File(self.filename, write_mode) as nxs:
            # NXentry and NXmx definition
            write_NXentry(nxs)

            # Write start time if known
            if start_time:
                write_NXdatetime(nxs, start_time, "start_time")

            # NXdata: entry/data
            write_NXdata(
                nxs,
                [metafile],
                "events",
                list(osc.keys())[0],
            )

            # NXinstrument: entry/instrument
            write_NXinstrument(
                nxs,
                self.beam,
                self.attenuator,
                self.source,
            )

            # NXdetector: entry/instrument/detector
            write_NXdetector(
                nxs,
                self.detector,
                meta=metafile,
            )

            # NXmodule: entry/instrument/detector/module
            write_NXdetector_module(
                nxs,
                module,
                self.detector.detector_params.image_size,
                self.detector.detector_params.pixel_size,
                beam_center=self.detector.beam_center,
            )

            # NXsource: entry/source
            write_NXsource(nxs, self.source)

            # NXsample: entry/sample
            write_NXsample(
                nxs,
                self.goniometer.axes_list,
                "events",
                osc,
                sample_depends_on=None,  # TODO
                add_nonstandard_fields=add_non_standard,
            )
