"""
A writer for NXmx format NeXus Files.
"""
from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import h5py
import numpy as np

from .. import MAX_FRAMES_PER_DATASET, MAX_SUFFIX_DIGITS, reframe_arrays
from ..nxs_utils.Detector import Detector
from ..nxs_utils.Goniometer import Goniometer
from ..nxs_utils.Source import Attenuator, Beam, Source
from ..tools.VDS_tools import clean_unused_links, image_vds_writer
from ..utils import get_filename_template
from .NXclassWriters import (
    write_NXcoordinate_system_set,
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

# Logger
nxmx_logger = logging.getLogger("nexgen.NXmxFileWriter")
nxmx_logger.setLevel(logging.DEBUG)

eiger_meta_links = [
    [
        "pixel_mask",
        "pixel_mask_applied",
        "flatfield",
        "flatfield_applied",
        "threshold_energy",
        "bit_depth_image",
        "detector_readout_time",
        "serial_number",
    ],
    ["software_version"],
]

# New Writer goes here
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

    def _get_meta_file(self, image_filename: str = None) -> Path:
        """Get filename_meta.h5 file in directory."""
        if image_filename:
            return self.filename.parent / f"{image_filename}_meta.h5"
        else:
            return self.filename.parent / f"{self.filename.stem}_meta.h5"

    def _get_data_files_list(
        self,
        image_filename: str | None = None,
    ) -> List[Path]:
        """Get list of datafiles.

        Args:
            image_filename (str | None, optional): Filename stem to use to look for image files. Needed in case it doesn't match \
                the NeXus file name. Defaults to None.

        Returns:
            List[Path]: List of data files to link to.
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
        nxmx_logger.info(f"Number of datafiles to be written: {len(datafiles)}.")
        return datafiles

    def _unpack_dictionaries(self) -> Tuple[Dict]:
        return (
            self.goniometer.to_dict(),
            self.detector.to_dict(),
            self.detector.to_module_dict(),
            self.source.to_dict(),
        )

    def update_timestamps(self, timestamps: Tuple[str, str]):
        """Save timestamps for start and end collection.

        Args:
            timestamps (Tuple[str, str]): Timestamps.
        """
        with h5py.File(self.filename, "r+") as nxs:
            write_NXdatetime(nxs, timestamps)
        nxmx_logger.info("Start and end collection timestamp updated.")

    def add_NXnote(self, notes: Dict, loc: str = "/entry/notes"):
        """Save any additional information as NXnote at the end of the collection.

        Args:
            notes (Dict): Dictionary of (key, value) pairs where key represents the dataset name and value its data.
            loc (str, optional): Location in the NeXus file to save metadata. Defaults to "/entry/notes".
        """
        with h5py.File(self.filename, "r+") as nxs:
            write_NXnote(nxs, loc, notes)
        nxmx_logger.info(f"Notes saved in {loc}.")

    def write(
        self,
        image_datafiles: List | None = None,
        image_filename: str | None = None,
        start_time: str | None = None,
    ):
        """Write the NXmx format NeXus file.

        This function calls the writers for the main NXclass objects.

        Args:
            image_datafiles (List | None, optional): List of image data files. If not passed, the program will look for \
                files with the stem_######.h5 in the target directory. Defaults to None.
            image_filename (str | None, optional): Filename stem to use to look for image files. Needed in case it doesn't match \
                the NeXus file name. Format: filename_runnumber. Defaults to None.
            start_time (str, optional): Collection start time if already available, in the format "%Y-%m-%dT%H:%M:%SZ". Defaults to None.
        """
        metafile = self._get_meta_file(image_filename)
        datafiles = (
            image_datafiles
            if image_datafiles
            else self._get_data_files_list(image_filename)
        )

        gonio, det, module, source = self._unpack_dictionaries()

        osc, transl = self.goniometer.define_scan_from_goniometer_axes()

        link_list = eiger_meta_links if "eiger" in det["description"].lower() else None

        with h5py.File(self.filename, "x") as nxs:
            # NXentry and NXmx definition
            write_NXentry(nxs)

            # Start time if known
            if start_time:
                write_NXdatetime(nxs, (start_time, None))

            # NXdata: entry/data
            write_NXdata(
                nxs,
                datafiles,
                gonio,
                "images",
                osc,
                transl,
            )

            # NXinstrument: entry/instrument
            write_NXinstrument(
                nxs,
                self.beam.to_dict(),
                self.attenuator.to_dict(),
                source,
            )

            # NXdetector: entry/instrument/detector
            write_NXdetector(
                nxs,
                det,
                ("images", self.tot_num_imgs),
                metafile,
                link_list,
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
            write_NXsource(nxs, source)

            # NXsample: entry/sample
            write_NXsample(
                nxs,
                gonio,
                "images",
                osc,
                transl,
                sample_depends_on=None,  # TODO
            )

    def write_vds(
        self,
        vds_offset: int = 0,
        vds_shape: Tuple[int, int, int] = None,
        vds_dtype: Any = np.uint16,
    ):
        """Write a Virtual Dataset.

        This method adds a VDS under /entry/data/data in the NeXus file, linking to either the full datasets or the subset defined by \
        vds_offset (used as start index) and vds_shape.

        Args:
            vds_offset (int, optional): Start index for the vds writer. Defaults to 0.
            vds_shape (Tuple[int,int,int], optional): Shape of the data which will be linked in the VDS. If not passed, it will be defined as \
            (tot_num_imgs - start_idx, *image_size). Defaults to None.
            vds_dtype (Any, optional): The type of the input data. Defaults to np.uint16.
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

        nxmx_logger.info(f"VDS shape set to {vds_shape}.")

        with h5py.File(self.filename, "r+") as nxs:
            image_vds_writer(
                nxs,
                (self.tot_num_imgs, *self.detector.detector_params.image_size),
                start_index=vds_offset,
                vds_shape=vds_shape,
                data_type=vds_dtype,
            )
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

    def write(self):
        """Write a NXmx-like NeXus file for event mode data collections.

        This method overrides the write() method of NXmxFileWriter, from which thsi class inherits.
        """
        # Get metafile
        # No data files, just link to meta
        metafile = super()._get_meta_file()

        # Unpack
        gonio, det, module, source = super()._unpack_dictionaries()

        # Get scan info
        # Here no scan, just get (start, stop) from omega/phi as osc and None as transl
        osc, _ = self.goniometer.define_scan_axes_for_event_mode(self.end_pos)

        with h5py.File(self.filename, "x") as nxs:
            # NXentry and NXmx definition
            write_NXentry(nxs)

            # NXdata: entry/data
            write_NXdata(
                nxs,
                [metafile],
                gonio,
                "events",
                osc,
            )

            # NXinstrument: entry/instrument
            write_NXinstrument(
                nxs,
                self.beam.to_dict(),
                self.attenuator.to_dict(),
                source,
            )

            # NXdetector: entry/instrument/detector
            write_NXdetector(
                nxs,
                det,
                ("events", None),
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
            write_NXsource(nxs, source)

            # NXsample: entry/sample
            write_NXsample(
                nxs,
                gonio,
                "events",
                osc,
                sample_depends_on=None,  # TODO
            )


class EDNXmxFileWriter(NXmxFileWriter):
    """A class to generate NXmx-like NeXus files for electron diffraction."""

    def __init__(
        self,
        filename: Path | str,
        goniometer: Goniometer,
        detector: Detector,
        source: Source,
        beam: Beam,
        attenuator: Attenuator,
        tot_num_imgs: int,
        ED_coord_system: Dict,
        coordinate_frame: str = "mcstas",
    ):
        super().__init__(
            filename,
            goniometer,
            detector,
            source,
            beam,
            attenuator,
            tot_num_imgs,
        )
        self.ED_coord_system = ED_coord_system
        self.coord_frame = coordinate_frame

    def write(
        self,
        image_datafiles: List | None = None,
        vds: bool = False,
        data_entry_key: str = "/entry/data/data",
    ):
        """Write a NXmx-like NeXus file for electron diffraction.

        This method overrides the write() method of NXmxFileWriter, from which thsi class inherits.
        In particular, it performs a few checks on the coordinate frame of the input vectors \
        and then calls the writers for the relevant NeXus base classes.

        Args:
            image_datafiles (List | None, optional): List of image data files. If not passed, the program will look for \
                files with the stem_######.h5 in the target directory. Defaults to None.
            vds (bool, optional): Write a VDS as entry/data/data if True. Defaults to False.
        """
        # Get data files
        datafiles = (
            image_datafiles if image_datafiles else super()._get_data_files_list()[0]
        )

        # Unpack
        gonio, det, module, source = self._unpack_dictionaries()

        # Scans
        osc, _ = self.goniometer.define_scan_from_goniometer_axes()

        # Deal with vecotrs/offsets/whatever
        reframe_arrays(
            gonio,
            det,
            module,
            self.coord_frame,
            self.ED_coord_system,
        )

        with h5py.File(self.filename, "x") as nxs:
            # NXentry and NXmx definition
            write_NXentry(nxs)

            # NXcoordinate_system_set: /entry/coordinate_system_set
            base_vectors = {k: self.ED_coord_system.get(k) for k in ["x", "y", "z"]}
            write_NXcoordinate_system_set(
                nxs,
                self.ED_coord_system["convention"],
                base_vectors,
                self.ED_coord_system["origin"],
            )

            # NXdata: entry/data
            write_NXdata(
                nxs,
                datafiles,
                gonio,
                "images",
                osc,
                entry_key=data_entry_key,
            )

            # NXinstrument: entry/instrument
            write_NXinstrument(
                nxs,
                self.beam.to_dict(),
                self.attenuator.to_dict(),
                source,
            )

            # NXdetector: entry/instrument/detector
            write_NXdetector(
                nxs,
                det,
                ("images", self.tot_num_imgs),
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
            write_NXsource(nxs, source)

            # NXsample: entry/sample
            write_NXsample(
                nxs,
                gonio,
                "images",
                osc,
            )

            # write vds
            if vds is True:
                image_vds_writer(
                    nxs,
                    (self.tot_num_imgs, *self.detector.detector_params.image_size),
                    entry_key=data_entry_key,
                )
