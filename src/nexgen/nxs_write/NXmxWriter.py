"""
A writer for NXmx format NeXus Files.
"""
from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Dict, List, Tuple

import h5py

from ..nxs_utils.Detector import Detector
from ..nxs_utils.Goniometer import Goniometer
from ..nxs_utils.Source import Attenuator, Beam, Source
from ..tools.VDS_tools import image_vds_writer
from ..utils import get_filename_template
from .NXclassWriters import (
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
        "bit_depth_readout",
        "detector_readout_time",
        "serial_number",
    ],
    ["software_version"],
]

# New Writer goes here
class NXmxFileWriter:
    def __init__(
        self,
        filename: Path | str,
        goniometer: Goniometer,
        detector: Detector,
        source: Source,
        beam: Beam,
        attenuator: Attenuator,
        tot_num_imgs: int,  # | None = None,
        # **scan_params,
    ):
        self.filename = Path(filename).expanduser().resolve()
        self.goniometer = goniometer
        self.detector = detector
        self.source = source
        self.beam = beam
        self.attenuator = attenuator
        self.tot_num_imgs = tot_num_imgs
        # Anything else in the future (?)

    @staticmethod
    def update_timestamps(filename: Path | str, timestamps: Tuple[str, str]):
        """Save timestamps for start and end collection."""
        with h5py.File(filename, "r+") as nxs:
            write_NXdatetime(nxs, timestamps)
        nxmx_logger.info("Start and end collection timestamp updated.")

    @staticmethod
    def add_NXnote(filename: Path | str, notes: Dict, loc: str = "/entry/notes"):
        with h5py.File(filename, "r+") as nxs:
            write_NXnote(nxs, loc, notes)
        nxmx_logger.info(f"Notes saved in {loc}.")

    def _find_meta_file(self) -> Path:
        """Find meta.h5 file in directory."""
        metafile = [
            f
            for f in self.filename.parent.iterdir()
            if self.filename.stem + "_meta" in f.as_posix()
        ][0]
        nxmx_logger.info(f"Found {metafile} in directory.")
        return metafile

    def _get_data_files_list(self, max_imgs_per_file: int = 1000) -> List[Path]:
        """Get list of datafiles."""
        num_files = math.ceil(self.tot_num_imgs / max_imgs_per_file)
        template = get_filename_template(self.filename)
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

    def write(self, vds: bool = False, vds_offset: int = 0):
        metafile = self._find_meta_file()
        datafiles = self._get_data_files_list()

        gonio, det, module, source = self._unpack_dictionaries()

        osc, transl = self.goniometer.define_scan_from_goniometer_axes()

        link_list = eiger_meta_links if "eiger" in det["description"].lower() else None

        # TODO IMPROVE THIS
        with h5py.File(self.filename, "x") as nxs:
            # NXentry and NXmx definition
            write_NXentry(nxs)

            # NXdata: entry/data
            write_NXdata(
                nxs,
                datafiles,
                gonio,
                ("images", self.tot_num_imgs),
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
                ("images", self.tot_num_imgs),
                osc,
                transl,
                sample_depends_on=None,  # TODO
            )

            # write vds
            if vds is True:
                image_vds_writer(
                    nxs,
                    (self.tot_num_imgs, *self.detector.detector_params.image_size),
                    start_index=vds_offset,
                )

    def write_for_events(self):
        # Placeholder for timepix writer
        # Here no scan, just get (start, stop) from omega/phi as osc and None as transl
        # Then call write I guess
        pass
