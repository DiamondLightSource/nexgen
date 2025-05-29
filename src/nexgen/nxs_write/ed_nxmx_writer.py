"""
A writer for NXmx-like NeXus files for electron diffraction.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import h5py
import numpy as np
from numpy.typing import DTypeLike

from ..nxs_utils import Attenuator, Beam, Detector, Goniometer, Source
from ..tools.vds_tools import image_vds_writer, vds_file_writer
from ..utils import coord2mcstas
from .nxclass_writers import (
    write_NXcoordinate_system_set,
    write_NXdata,
    write_NXdatetime,
    write_NXdetector,
    write_NXdetector_module,
    write_NXentry,
    write_NXinstrument,
    write_NXsample,
    write_NXsource,
)
from .write_utils import calculate_estimated_end_time

# Logger
edwriter_logger = logging.getLogger("nexgen.EDNXmxFileWriter")
edwriter_logger.setLevel(logging.DEBUG)


class EDNXmxFileWriter:
    """A class to generate NXmx-like NeXus files for electron diffraction.

    Requires a couple of additional arguments compared to a standard NXmxWriter:
        ED_coord_system (Dict): Definition of the current coordinate frame for ED. \
            It should at least contain the convention, origin and base vectors.
        convert_to_mcstas (bool, optional): If true, convert the vectors to mcstas. \
            Defaults to False.
    """

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
        convert_to_mcstas: bool = False,
    ):
        self.filename = Path(filename).expanduser().resolve()
        self.goniometer = goniometer
        self.detector = detector
        self.source = source
        self.beam = beam
        self.attenuator = attenuator
        self.tot_num_imgs = tot_num_imgs
        self.ED_coord_system = ED_coord_system
        self.convert_cs = convert_to_mcstas

    def _check_coordinate_frame(self):
        """Checks the coordinate frame and converts to mcstas if requested."""
        if self.convert_cs is True:
            edwriter_logger.warning(
                "All the vector/offset axis coordinates will be converted to mcstas."
            )
            mat = np.array(
                [
                    self.ED_coord_system["x"].vector,
                    self.ED_coord_system["y"].vector,
                    self.ED_coord_system["z"].vector,
                ]
            )
            # TODO: Need to redefine ED as {"x": Axis()} or something
            for ax in self.goniometer.axes_list:
                ax.vector = coord2mcstas(ax.vector, mat)
            for ax in self.detector.detector_axes:
                ax.vector = coord2mcstas(ax.vector, mat)
            self.detector.fast_axis = coord2mcstas(self.detector.fast_axis, mat)
            self.detector.slow_axis = coord2mcstas(self.detector.slow_axis, mat)

    def _get_data_filename(self) -> List[Path]:
        """Returns a list of data files."""
        image_filename = f"{self.filename.stem}_data_000001.h5"
        return self.filename.parent / f"{image_filename}"

    def _get_collection_time(self) -> float:
        """Returns total collection time."""
        return self.detector.exp_time * self.tot_num_imgs

    def write(
        self,
        image_datafiles: List | None = None,
        data_entry_key: str = "/entry/data/data",
        start_time: datetime | str | None = None,
        write_mode: str = "x",
    ):
        """Write a NXmx-like NeXus file for electron diffraction.

        This function calls the writers for the main NXclass objects.
        Additionally, it performs a few checks on the coordinate frame of the input vectors \
        and then calls the writers for the relevant NeXus base classes.

        Args:
            image_datafiles (List | None, optional): List of image data files. If not \
                passed, the program will look for files with the stem_data_######.h5 in \
                the target directory. Defaults to None.
            data_entry_key (str, optional): Dataset entry key in datafiles. Defaults to \
                entry/data/data.
            start_time (datetime | str, optional): Collection estimated end time if \
                available, in the format "%Y-%m-%dT%H:%M:%SZ". Defaults to None.
            write_mode (str, optional): String indicating writing mode for the output \
                NeXus file. Accepts any valid h5py file opening mode. Defaults to "x".
        """
        # Get data files
        datafiles = image_datafiles if image_datafiles else [self._get_data_filename()]

        module = self.detector.get_module_info()

        # Scans
        osc, _ = self.goniometer.define_scan_from_goniometer_axes()

        # Deal with vecotrs/offsets/whatever if needed
        self._check_coordinate_frame()

        # Get the instrument name
        instrument_name = self.source.set_instrument_name
        edwriter_logger.info(f"Instrument name will be set as {instrument_name}.")

        # NXcoordinate_system_set: /entry/coordinate_system_set
        base_vectors = {k: self.ED_coord_system.get(k) for k in ["x", "y", "z"]}

        with h5py.File(self.filename, write_mode) as nxs:
            # NXentry and NXmx definition
            write_NXentry(nxs)

            write_NXcoordinate_system_set(
                nxs,
                self.ED_coord_system["convention"],
                base_vectors,
                self.ED_coord_system["origin"],
            )

            if start_time:
                write_NXdatetime(nxs, start_time, "start_time")
                tot_exp_time = self._get_collection_time()
                est_end = calculate_estimated_end_time(start_time, tot_exp_time)
                write_NXdatetime(nxs, est_end, "end_time_estimated")

            # NXdata: entry/data
            write_NXdata(
                nxs,
                datafiles,
                "images",
                list(osc.keys())[0],
                entry_key=data_entry_key,
            )

            # NXinstrument: entry/instrument
            write_NXinstrument(
                nxs,
                self.beam,
                self.attenuator,
                self.source,
                reset_instrument_name=True,
            )

            # NXdetector: entry/instrument/detector
            write_NXdetector(
                nxs,
                self.detector,
                self.tot_num_imgs,
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
            )

    def write_vds(
        self,
        vds_dtype: DTypeLike = np.uint16,
        writer_type: str = "dataset",
        data_entry_key: str = "/entry/data/data",
        datafiles: List[Path] | None = None,
    ):
        """Write a vds for electron diffraction.

        This method adds a VDS under /entry/data/data in the NeXus file as a default.
        If instead the writer_type is set to "file" it will write an external _vds.h5 file.

        Args:
            vds_dtype (DTypeLike, optional): The type of the input data. Defaults to np.uint16.
            writer_type (str, optional): Type of vds required. Defaults to "dataset".
            data_entry_key (str, optional): Dataset entry key in datafiles. Defaults to "/entry/data/data".
            datafiles ((List | None, optional): List of image data files. If not passed, the program will look for \
                files with the stem_######.h5 in the target directory. Defaults to None.
        """
        if writer_type not in ["dataset", "file"]:
            edwriter_logger.warning(
                f"Writer type {writer_type} unknown. Will default to dataset."
            )
            writer_type = "dataset"
        with h5py.File(self.filename, "r+") as nxs:
            if writer_type == "dataset":
                edwriter_logger.debug(
                    "Writing vds dataset as /entry/data/data in nexus file."
                )
                image_vds_writer(
                    nxs,
                    (self.tot_num_imgs, *self.detector.detector_params.image_size),
                    data_type=vds_dtype,
                    entry_key=data_entry_key,
                )
            else:
                if not datafiles:
                    edwriter_logger.warning(
                        "No datafile list passed, vds file won't be written."
                    )
                    return
                edwriter_logger.info(
                    "Writing external vds file with link in /entry/data/data in nexus file."
                )
                vds_file_writer(
                    nxs,
                    datafiles,
                    (self.tot_num_imgs, *self.detector.detector_params.image_size),
                    vds_dtype,
                    data_entry_key,
                )
