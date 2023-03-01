"""
A writer for NXmx format NeXus Files.
"""
from __future__ import annotations

import glob
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import h5py

# from .. import log
from ..nxs_utils.Detector import Detector
from ..nxs_utils.Goniometer import Goniometer
from ..nxs_utils.Source import Attenuator, Beam, Source

# from ..tools.VDS_tools import image_vds_writer
from .NXclassWriters import write_NXdatetime, write_NXnote

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
        # tot_num_imgs: Tuple[int] | None = None,  # If not passed can be found from scans
        # **scan_params,
    ):
        self.filename = Path(filename).expanduser().resolve()
        self.goniometer = goniometer
        self.detector = detector
        self.source = source
        self.beam = beam
        self.attenuator = attenuator
        # Anything else in the future (?)

    @staticmethod
    def update_end_timestamps(filename: Path | str, timestamp: str):
        with h5py.File(filename, "w") as nxs:
            write_NXdatetime(nxs, (None, timestamp))
        nxmx_logger.info("End collection timestamp updated.")

    @staticmethod
    def add_NXnote(filename: Path | str, notes: Dict, loc: str = "/entry/notes"):
        with h5py.File(filename, "w") as nxs:
            write_NXnote(nxs, loc, notes)
        nxmx_logger.info(f"Notes saved in {loc}.")

    def _find_meta_file(self) -> Path:
        metafile = [
            f
            for f in self.filename.parent.iterdir()
            if self.filename.stem + "_meta" in f.as_posix()
        ][0]
        nxmx_logger.info(f"Found {metafile} in directory.")
        return metafile

    def _find_data_files(self) -> List[Path]:
        template = self.filename.parent / self.filename.name.replace(
            ".nxs", f"_{6*'[0-9]'}.h5"
        )
        datafiles = [
            Path(f).expanduser().resolve()
            for f in sorted(glob.glob(template.as_posix()))
        ]
        return datafiles

    def _unpack_dictionaries(self) -> Tuple[Dict]:
        return (
            self.goniometer._generate_goniometer_dict(),
            self.detector._generate_detector_dict(),
            self.detector._generate_module_dict(),
            self.source._generate_source_dict(),
            self.beam.to_dict(),
            self.attenuator.to_dict(),
        )

    def write(self, vds: bool = False, vds_offset: int = 0):
        gonio, det, module, source, beam, att = self._unpack_dictionaries()
        pass

    def write_for_events():
        # Placeholder for timepix writer
        # Here no scan, just get (start, stop) from omega/phi as osc and None as transl
        # Then call write I guess
        pass


# For now, just used call writers.
# To be removed when everything else works AND images/event functions are separated
