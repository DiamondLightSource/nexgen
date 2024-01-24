"""
Writer functions for different groups of a NeXus file.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, get_args

import h5py  # isort: skip
import numpy as np
from numpy.typing import ArrayLike

from ..nxs_utils import (
    Attenuator,
    Axis,
    Beam,
    Detector,
    DetectorType,
    EigerDetector,
    Source,
)
from ..utils import (
    MAX_SUFFIX_DIGITS,
    get_iso_timestamp,
    units_of_length,
    units_of_time,
    ureg,
)
from .write_utils import (
    TSdset,
    calculate_origin,
    create_attributes,
    set_dependency,
    write_compressed_copy,
)

NXclass_logger = logging.getLogger("nexgen.NXclass_writers")
NXclass_logger.setLevel(logging.DEBUG)


# NXentry writer
def write_NXentry(nxsfile: h5py.File, definition: str = "NXmx") -> h5py.Group:
    """
    Write NXentry group at top level of the NeXus file.
    Also, write the application definition NXmx.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        definition (str, optional): Application definition for NeXus file. Defaults to "NXmx".

    Returns:
        nxentry (h5py.Group): NXentry group.
    """
    # Set default attribute
    nxsfile.attrs["default"] = "entry"

    # Start writing the NeXus tree with NXentry at the top level
    nxentry = nxsfile.require_group("entry")
    create_attributes(
        nxentry, ("NX_class", "default", "version"), ("NXentry", "data", "1.0")
    )

    # Application definition: /entry/definition
    nxentry.create_dataset("definition", data=np.string_(definition))
    return nxentry


# NXdata writer
def write_NXdata(
    nxsfile: h5py.File,
    datafiles: List[Path],
    goniometer_axes: List[Axis],
    data_type: str,
    osc_scan: Dict[str, ArrayLike],
    transl_scan: Dict[str, ArrayLike] = None,
    entry_key: str = "data",
):
    """
    Write NXdata group at /entry/data.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        datafiles (List[Path]): List of Path objects pointing to HDF5 data files.
        goniometer_axes (List[Axis]): List of goniometer axes.
        data_type (str): Images or events.
        osc_scan (Dict[str, ArrayLike]): Rotation scan. If writing events, this is just a (start, end) tuple.
        transl_scan (Dict[str, ArrayLike], optional): Scan along the xy axes at sample. Defaults to None.
        entry_key (str): Entry key to create the external links to the data files. Defaults to data.

    Raises:
        OSError: If no data is passed.
        ValueError: If the data typs is neither "images" nor "events".
    """
    NXclass_logger.info("Start writing NXdata.")
    # Check that a valid datafile_list has been passed.
    if len(datafiles) == 0:
        raise OSError(
            "No HDF5 data filenames have been found. Please pass at least one."
        )

    # This assumes that a rotation scan is always passed
    osc_axis, osc_range = list(osc_scan.items())[0]

    # Create NXdata group, unless it already exists, in which case just open it.
    nxdata = nxsfile.require_group("/entry/data")
    create_attributes(
        nxdata,
        ("NX_class", "axes", "signal", osc_axis + "_indices"),
        (
            "NXdata",
            osc_axis,
            "data",
            [
                0,
            ],
        ),
    )

    # If mode is images, link to blank image data. Else go to events.
    if data_type == "images":
        tmp_name = f"data_%0{MAX_SUFFIX_DIGITS}d"
        if datafiles[0].parent != Path(nxsfile.filename).parent:
            # This is needed in case the new NeXus file is to be written in a different directory from the data, eg. processing/
            for n, filename in enumerate(datafiles):
                nxdata[tmp_name % (n + 1)] = h5py.ExternalLink(filename, entry_key)
        else:
            for n, filename in enumerate(datafiles):
                nxdata[tmp_name % (n + 1)] = h5py.ExternalLink(filename.name, entry_key)
    elif data_type == "events":
        if len(datafiles) == 1 and "meta" in datafiles[0].as_posix():
            meta = datafiles
        else:
            # Look for meta file to avoid linking to up to 100 files
            tbr = datafiles[0].stem.split("_")[-1]
            mf = datafiles[0].stem.replace(tbr, "meta") + datafiles[0].suffix
            meta = [f for f in datafiles[0].parent.iterdir() if mf in f.as_posix()]
        # If metafile is not found, link to the data files
        if len(meta) == 0:
            for filename in datafiles:
                nxdata[filename.stem] = h5py.ExternalLink(filename.name, "/")
        else:
            nxdata["meta_file"] = h5py.ExternalLink(meta[0].name, "/")
    else:
        raise ValueError(
            "Unknown data type. Please pass one value for data_type from : [images, events]"
        )

    # Write rotation axis dataset
    ax = nxdata.create_dataset(osc_axis, data=osc_range)
    idx = [n for n, ax in enumerate(goniometer_axes) if ax.name == osc_axis][0]
    dep = set_dependency(
        goniometer_axes[idx].depends, path="/entry/sample/transformations/"
    )

    # Write attributes for axis
    create_attributes(
        ax,
        ("depends_on", "transformation_type", "units", "vector"),
        (
            dep,
            goniometer_axes[idx].transformation_type,
            goniometer_axes[idx].units,
            goniometer_axes[idx].vector,
        ),
    )

    # If present, add linear/grid scan details
    if transl_scan:
        for k, v in transl_scan.items():
            ax_dset = nxdata.create_dataset(k, data=v)
            ax_idx = [n for n, ax in enumerate(goniometer_axes) if ax.name == k][0]
            ax_dep = set_dependency(
                goniometer_axes[ax_idx].depends, path="/entry/sample/transformations/"
            )
            create_attributes(
                ax_dset,
                ("depends_on", "transformation_type", "units", "vector"),
                (
                    ax_dep,
                    goniometer_axes[ax_idx].transformation_type,
                    goniometer_axes[ax_idx].units,
                    goniometer_axes[ax_idx].vector,
                ),
            )


# NXsample
def write_NXsample(
    nxsfile: h5py.File,
    goniometer_axes: List[Axis],
    data_type: str,
    osc_scan: Dict[str, ArrayLike],
    transl_scan: Dict[str, ArrayLike] = None,
    sample_depends_on: str = None,
    sample_details: Dict[str, Any] = None,
):
    """
    Write NXsample group at /entry/sample.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        goniometer_axes (List[Axis]): List of goniometer axes.
        data_type (str): Images or events.
        osc_scan (Dict[str, ArrayLike]): Rotation scan. If writing events, this is just a (start, end) tuple.
        transl_scan (Dict[str, ArrayLike], optional): Scan along the xy axes at sample. Defaults to None.
        sample_depends_on (str, optional): Axis on which the sample depends on. If absent, the depends_on field will be set to the last axis listed in the goniometer. Defaults to None.
        sample_details (Dict[str, Any], optional): General information about the sample, eg. name, temperature.
    """
    NXclass_logger.info("Start writing NXsample and NXtransformations.")
    # Create NXsample group, unless it already exists, in which case just open it.
    nxsample = nxsfile.require_group("/entry/sample")
    create_attributes(
        nxsample,
        ("NX_class",),
        ("NXsample",),
    )

    # Create NXtransformations group: /entry/sample/transformations
    nxtransformations = nxsample.require_group("transformations")
    create_attributes(
        nxtransformations,
        ("NX_class",),
        ("NXtransformations",),
    )

    # Get rotation details
    osc_axis, osc_range = list(osc_scan.items())[0]

    # Save sample depends_on
    if sample_depends_on:
        nxsample.create_dataset(
            "depends_on",
            data=set_dependency(sample_depends_on, path=nxtransformations.name),
        )
    else:
        nxsample.create_dataset(
            "depends_on",
            data=set_dependency(goniometer_axes[-1].name, path=nxtransformations.name),
        )

    # Get xy details if passed
    scan_axes = []
    if transl_scan:
        for k in transl_scan.keys():
            scan_axes.append(k)

    # Create sample_{axisname} groups
    for idx, ax in enumerate(goniometer_axes):
        axis_name = ax.name
        grp_name = (
            f"sample_{axis_name[-1]}" if "sam_" in axis_name else f"sample_{axis_name}"
        )
        nxsample_ax = nxsample.create_group(grp_name)
        create_attributes(nxsample_ax, ("NX_class",), ("NXpositioner",))
        if axis_name == osc_axis:
            # If we're dealing with the scan axis
            if (
                "data" in nxsfile["/entry"].keys()
                and axis_name in nxsfile["/entry/data"].keys()
            ):
                nxsample_ax[axis_name] = nxsfile[nxsfile["/entry/data"][axis_name].name]
                nxtransformations[axis_name] = nxsfile[
                    nxsfile["/entry/data"][axis_name].name
                ]
            else:
                nxax = nxsample_ax.create_dataset(axis_name, data=osc_range)
                _dep = set_dependency(
                    goniometer_axes[idx].depends, path="/entry/sample/transformations/"
                )
                create_attributes(
                    nxax,
                    ("depends_on", "transformation_type", "units", "vector"),
                    (
                        _dep,
                        goniometer_axes[idx].transformation_type,
                        goniometer_axes[idx].units,
                        goniometer_axes[idx].vector,
                    ),
                )
                nxtransformations[axis_name] = nxsfile[nxax.name]
            # Write {axisname}_increment_set and {axis_name}_end datasets
            if data_type == "images":
                increment_set = np.repeat(
                    goniometer_axes[idx].increment, len(osc_range)
                )
                nxsample_ax.create_dataset(
                    axis_name + "_increment_set",
                    data=goniometer_axes[idx].increment,
                )  # increment_set
                nxsample_ax.create_dataset(
                    axis_name + "_end", data=osc_range + increment_set
                )
        elif axis_name in scan_axes:
            # For translations
            if (
                "data" in nxsfile["/entry"].keys()
                and axis_name in nxsfile["/entry/data"].keys()
            ):
                nxsample_ax[axis_name] = nxsfile[nxsfile["/entry/data"][axis_name].name]
                nxtransformations[axis_name] = nxsfile[
                    nxsfile["/entry/data"][axis_name].name
                ]
            else:
                nxax = nxsample_ax.create_dataset(
                    axis_name, data=transl_scan[axis_name]
                )
                _dep = set_dependency(
                    goniometer_axes[idx].depends, path="/entry/sample/transformations/"
                )
                create_attributes(
                    nxax,
                    ("depends_on", "transformation_type", "units", "vector"),
                    (
                        _dep,
                        goniometer_axes[idx].transformation_type,
                        goniometer_axes[idx].units,
                        goniometer_axes[idx].vector,
                    ),
                )
                nxtransformations[axis_name] = nxsfile[nxax.name]
        else:
            # For all other axes
            nxax = nxsample_ax.create_dataset(
                axis_name, data=np.array([goniometer_axes[idx].start_pos])
            )
            _dep = set_dependency(
                goniometer_axes[idx].depends, path="/entry/sample/transformations/"
            )
            create_attributes(
                nxax,
                ("depends_on", "transformation_type", "units", "vector"),
                (
                    _dep,
                    goniometer_axes[idx].transformation_type,
                    goniometer_axes[idx].units,
                    goniometer_axes[idx].vector,
                ),
            )
            nxtransformations[axis_name] = nxsfile[nxax.name]

    # Look for nxbeam in file, if it's there make link
    try:
        nxsample["beam"] = nxsfile["/entry/instrument/beam"]
    except KeyError:
        NXclass_logger.debug(
            "No NXbeam group found elsewhere in the NeXus file." "No link written."
        )

    if sample_details:
        for k, v in sample_details.items():
            if isinstance(v, str):
                v = np.string_(v)
            nxsample.create_dataset(k, data=v)


# NXinstrument
def write_NXinstrument(
    nxsfile: h5py.File,
    beam: Beam,
    attenuator: Attenuator,
    source: Source,
    reset_instrument_name: bool = False,
):
    """
    Write NXinstrument group at /entry/instrument.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        beam (Dict):Dictionary with beam information, mainly wavelength and flux.
        attenuator (Dict): Dictionary containing transmission.
        source (Source): Source definition, containing the facility information.
        reset_instrument_name (bool, optional): If True, a string with the name of the \
            instrument used. Otherwise, it will be set to 'DIAMOND BEAMLINE Ixx'. Defaults to False.
    """
    NXclass_logger.info("Start writing NXinstrument.")
    # Create NXinstrument group, unless it already exists, in which case just open it.
    nxinstrument = nxsfile.require_group("/entry/instrument")
    create_attributes(
        nxinstrument,
        ("NX_class",),
        ("NXinstrument",),
    )

    # Write /name field and relative attribute
    NXclass_logger.info(f"{source.short_name} {source.beamline}")
    name_str = (
        source.set_instrument_name()
        if reset_instrument_name
        else f"DIAMOND BEAMLINE {source.beamline}"
    )
    nxinstrument.create_dataset("name", data=np.string_(name_str))
    create_attributes(
        nxinstrument["name"],
        ("short_name",),
        (f"{source.short_name} {source.beamline}",),
    )

    NXclass_logger.info("Write NXattenuator and NXbeam.")
    # Write NXattenuator group: entry/instrument/attenuator
    nxatt = nxinstrument.require_group("attenuator")
    create_attributes(nxatt, ("NX_class",), ("NXattenuator",))
    if attenuator.transmission:
        nxatt.create_dataset(
            "attenuator_transmission",
            data=attenuator.transmission,
        )

    # Write NXbeam group: entry/instrument/beam
    nxbeam = nxinstrument.require_group("beam")
    create_attributes(nxbeam, ("NX_class",), ("NXbeam",))
    wl = nxbeam.create_dataset("incident_wavelength", data=beam.wavelength)
    create_attributes(wl, ("units",), ("angstrom",))
    if beam.flux:
        flux = nxbeam.create_dataset("total_flux", data=beam.flux)
        create_attributes(flux, ("units"), ("Hz",))


# NXsource
def write_NXsource(nxsfile: h5py.File, source: Source):
    """
    Write NXsource group /in entry/source.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        source (Source): Source definition, containing the facility information.
    """
    NXclass_logger.info("Start writing NXsource.")
    nxsource = nxsfile.require_group("/entry/source")
    create_attributes(
        nxsource,
        ("NX_class",),
        ("NXsource",),
    )

    nxsource.create_dataset("name", data=np.string_(source.name))
    create_attributes(nxsource["name"], ("short_name",), (source.short_name,))
    nxsource.create_dataset("type", data=np.string_(source.facility_type))
    if source.probe:
        nxsource.create_dataset("probe", data=np.string_(source.probe))


# NXdetector writer
def write_NXdetector(
    nxsfile: h5py.File,
    detector: Detector,
    num_images: int = None,
    meta: Path = None,
):
    """
    Write_NXdetector group at /entry/instrument/detector.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        detector (Detector): Detector definition.
        num_images (int, optional): Total number of images in collections. Defaults to None
        meta (Path, optional): Path to _meta.h5 file. Defaults to None.
    """
    NXclass_logger.info("Start writing NXdetector.")
    # Create NXdetector group, unless it already exists, in which case just open it.
    nxdetector = nxsfile.require_group("/entry/instrument/detector")
    create_attributes(
        nxdetector,
        ("NX_class",),
        ("NXdetector",),
    )

    # Detector description
    nxdetector.create_dataset(
        "description", data=np.string_(detector.detector_params.description)
    )
    nxdetector.create_dataset(
        "type", data=np.string_(detector.detector_params.detector_type)
    )

    collection_mode = detector.get_detector_mode()

    # If there is a meta file, a lot of information will be linked instead of copied
    if isinstance(detector.detector_params, EigerDetector):
        if meta:
            NXclass_logger.info(f"Found metadata in {meta.as_posix()} file.")
            meta_link = (
                meta.name
                if meta.parent == Path(nxsfile.filename).parent
                else meta.as_posix()
            )
            for k, v in detector.detector_params.constants.items():
                if k == "software_version":
                    # Software version should go in detectorSpecific (NXcollection)
                    break
                nxdetector[k] = h5py.ExternalLink(meta_link, v)
        else:
            NXclass_logger.warning(
                """
                Meta file for Eiger detector hasn't been specified.
                No links will be written. Pixel mask and flatfield information missing.
                """
            )
    else:
        # If it's an eiger mask and flatfield will be in the links along with other info.
        # If it isn't, the mask and flatfield info still needs to go in
        NXclass_logger.info("Gathering and writing pixel_mask and flatfield to file.")
        pixel_mask_file = detector.detector_params.constants["pixel_mask"]
        flatfield_file = detector.detector_params.constants["flatfield"]
        if collection_mode == "events":
            wd = Path(nxsfile.filename).parent
            # Bad pixel mask
            if pixel_mask_file:
                nxdetector.create_dataset(
                    "pixel_mask_applied",
                    data=detector.detector_params.constants["pixel_mask_applied"],
                )
                NXclass_logger.info(
                    f"Looking for file {pixel_mask_file} in {wd.as_posix()}."
                )
                maskfile = [
                    wd / pixel_mask_file
                    for f in wd.iterdir()
                    if pixel_mask_file == f.name
                ]
                if maskfile:
                    NXclass_logger.info("Pixel mask file found in working directory.")
                    write_compressed_copy(
                        nxdetector,
                        "pixel_mask",
                        filename=maskfile[0],
                        filter_choice="blosc",
                        dset_key="image",
                    )
                else:
                    NXclass_logger.warning(
                        "No pixel mask file found in working directory."
                        "Writing and ExternalLink."
                    )
                    mask = Path(pixel_mask_file)
                    image_key = (
                        "image"
                        if "tristan" in detector.detector_params.description.lower()
                        else "/"
                    )
                    nxdetector["pixel_mask"] = h5py.ExternalLink(mask.name, image_key)
            # Flatfield
            if flatfield_file:
                nxdetector.create_dataset(
                    "flatfield_applied",
                    data=detector.detector_params.constants["flatfield_applied"],
                )
                NXclass_logger.info(
                    f"Looking for file {flatfield_file} in {wd.as_posix()}."
                )
                flatfieldfile = [
                    wd / flatfield_file
                    for f in wd.iterdir()
                    if flatfield_file == f.name
                ]
                if flatfieldfile:
                    NXclass_logger.info("Flatfield file found in working directory.")
                    write_compressed_copy(
                        nxdetector,
                        "flatfield",
                        filename=flatfieldfile[0],
                        filter_choice="blosc",
                        dset_key="image",
                    )
                else:
                    NXclass_logger.warning(
                        "No flatfield file found in the working directory."
                        "Writing an ExternalLink."
                    )
                    flatfield = Path(flatfield_file)
                    image_key = (
                        "image"
                        if "tristan" in detector.detector_params.description.lower()
                        else "/"
                    )
                    nxdetector["flatfield"] = h5py.ExternalLink(
                        flatfield.name, image_key
                    )
        else:
            # Flatfield
            if isinstance(flatfield_file, str):
                nxdetector.create_dataset(
                    "flatfield_applied",
                    data=detector.detector_params.constants["flatfield_applied"],
                )
                flatfield = Path(flatfield_file)
                nxdetector["flatfield"] = h5py.ExternalLink(flatfield.name, "/")
            elif not flatfield_file:
                NXclass_logger.warning(
                    "No copy of the flatfield has been found, either as a file or dataset."
                )
            else:
                nxdetector.create_dataset(
                    "flatfield_applied",
                    data=detector.detector_params.constants["flatfield_applied"],
                )
                write_compressed_copy(nxdetector, "flatfield", data=flatfield_file)
            # Bad pixel mask
            if isinstance(pixel_mask_file, str):
                nxdetector.create_dataset(
                    "pixel_mask_applied",
                    data=detector.detector_params.constants["pixel_mask_applied"],
                )
                mask = Path(pixel_mask_file)
                nxdetector["pixel_mask"] = h5py.ExternalLink(mask.name, "/")
            elif not pixel_mask_file:
                NXclass_logger.warning(
                    "No copy of the pixel_mask has been found, eithere as a file or dataset."
                )
            else:
                nxdetector.create_dataset(
                    "pixel_mask_applied",
                    data=detector.detector_params.constants["pixel_mask_applied"],
                )
                write_compressed_copy(nxdetector, "pixel_mask", data=pixel_mask_file)

    # Beam center
    beam_center_x = nxdetector.create_dataset(
        "beam_center_x", data=detector.beam_center[0]
    )
    create_attributes(beam_center_x, ("units",), ("pixels",))
    beam_center_y = nxdetector.create_dataset(
        "beam_center_y", data=detector.beam_center[1]
    )
    create_attributes(beam_center_y, ("units",), ("pixels",))

    # Pixel size in m
    x_pix = units_of_length(detector.detector_params.pixel_size[0], True)
    x_pix_size = nxdetector.create_dataset("x_pixel_size", data=x_pix.magnitude)
    create_attributes(x_pix_size, ("units",), (format(x_pix.units, "~"),))
    y_pix = units_of_length(detector.detector_params.pixel_size[1], True)
    y_pix_size = nxdetector.create_dataset("y_pixel_size", data=y_pix.magnitude)
    create_attributes(y_pix_size, ("units",), (format(y_pix.units, "~"),))

    # Sensor material, sensor thickness in m
    nxdetector.create_dataset(
        "sensor_material", data=np.string_(detector.detector_params.sensor_material)
    )
    sensor_thickness = units_of_length(detector.detector_params.sensor_thickness, True)
    nxdetector.create_dataset("sensor_thickness", data=sensor_thickness.magnitude)
    create_attributes(
        nxdetector["sensor_thickness"],
        ("units",),
        (format(sensor_thickness.units, "~"),),
    )

    # Count time
    exp_time = units_of_time(detector.exp_time)
    nxdetector.create_dataset("count_time", data=exp_time.magnitude)

    # If detector mode is images write overload and underload
    if collection_mode == "images":
        nxdetector.create_dataset(
            "saturation_value", data=detector.detector_params.overload
        )
        nxdetector.create_dataset(
            "underload_value", data=detector.detector_params.underload
        )

    # Write_NXcollection
    write_NXcollection(
        nxdetector, detector.detector_params, collection_mode, num_images, meta
    )

    # Write NXtransformations: entry/instrument/detector/transformations/detector_z and two_theta
    nxtransformations = nxdetector.require_group("transformations")
    create_attributes(
        nxtransformations,
        ("NX_class",),
        ("NXtransformations",),
    )

    # Create groups for detector_z and any other detector axis (eg. two_theta) if present
    # This assumes that the detector axes are fixed.
    for idx, ax in enumerate(detector.detector_axes):
        if ax.name == "det_z":
            grp_name = "detector_z"
            dist = units_of_length(str(detector.detector_axes[idx].start_pos) + "mm")
        else:
            grp_name = ax.name

        # It shouldn't be too much of an issue but just in case ...
        if detector.detector_axes[idx].depends == "det_z":
            grp_dep = "detector_z"
        else:
            grp_dep = detector.detector_axes[idx].depends
        _dep = set_dependency(
            detector.detector_axes[idx].depends,
            nxtransformations.name + f"/{grp_dep}/",
        )

        nxgrp_ax = nxtransformations.create_group(grp_name)
        create_attributes(nxgrp_ax, ("NX_class",), ("NXpositioner",))
        nxdet_ax = nxgrp_ax.create_dataset(
            ax.name, data=np.array([detector.detector_axes[idx].start_pos])
        )
        create_attributes(
            nxdet_ax,
            ("depends_on", "transformation_type", "units", "vector"),
            (
                _dep,
                detector.detector_axes[idx].transformation_type,
                detector.detector_axes[idx].units,
                detector.detector_axes[idx].vector,
            ),
        )
        if ax.name == detector.detector_axes[-1].name:
            # Detector depends_on
            nxdetector.create_dataset(
                "depends_on",
                data=set_dependency(ax.name, path=nxgrp_ax.name),
            )

    # Write a soft link for detector_z
    if "detector_z" in list(nxtransformations.keys()):
        nxdetector["detector_z"] = nxsfile[
            "/entry/instrument/detector/transformations/detector_z"
        ]

    # Detector distance
    nxdetector.create_dataset("distance", data=dist.to("m").magnitude)
    create_attributes(
        nxdetector["distance"], ("units",), (format(dist.to("m").units, "~"))
    )

    # Check if there are any remaining datasets to be written (usually from the meta file but not always)
    others = [
        "threshold_energy",
        "bit_depth_image",
        "detector_number",
        "detector_readout_time",
        "photon_energy",
    ]
    for dset in others:
        if (
            nxdetector.__contains__(dset) is False
            and dset in detector.detector_params.constants.keys()
        ):
            val = (
                np.string_(detector.detector_params.constants[dset])
                if isinstance(detector.detector_params.constants[dset], str)
                else detector.detector_params.constants[dset]
            )
            if val is not None:
                nxdetector.create_dataset(dset, data=val)


# NXdetector_module writer
def write_NXdetector_module(
    nxsfile: h5py.File,
    module: Dict,
    image_size: List | Tuple,
    pixel_size: List | Tuple,
    beam_center: Optional[List | Tuple] = None,
):
    """
    Write NXdetector_module group at /entry/instrument/detector/module.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        module (Dict): Dictionary containing the detector module information: fast and slow axes, how many modules.
        image_size (List | Tuple): Size of the detector.
        pixel_size (List | Tuple): Size of the single pixels in fast and slow direction, in mm.
        beam_center (Optional[List | Tuple], optional): Beam center position, needed only if origin needs to be calculated. Defaults to None.
    """
    NXclass_logger.info("Start writing NXdetector_module.")
    # Create NXdetector_module group, unless it already exists, in which case just open it.
    nxmodule = nxsfile.require_group("/entry/instrument/detector/module")
    create_attributes(
        nxmodule,
        ("NX_class",),
        ("NXdetector_module",),
    )

    nxmodule.create_dataset("data_origin", data=np.array([0, 0]))
    nxmodule.create_dataset("data_size", data=image_size)
    nxmodule.create_dataset("data_stride", data=np.array([1, 1]))

    # Write fast_ and slow_ pixel_direction
    fast_axis = module["fast_axis"]
    slow_axis = module["slow_axis"]

    if "offsets" in module.keys():
        offsets = module["offsets"]
    else:
        offsets = [(0, 0, 0), (0, 0, 0)]

    x_pix = units_of_length(pixel_size[0], True)
    fast_pixel = nxmodule.create_dataset("fast_pixel_direction", data=x_pix.magnitude)
    create_attributes(
        fast_pixel,
        (
            "depends_on",
            "offset",
            "offset_units",
            "transformation_type",
            "units",
            "vector",
        ),
        (
            "/entry/instrument/detector/transformations/detector_z/det_z",
            offsets[0],
            "mm",
            "translation",
            format(x_pix.units, "~"),
            fast_axis,
        ),
    )

    y_pix = units_of_length(pixel_size[1], True)
    slow_pixel = nxmodule.create_dataset("slow_pixel_direction", data=y_pix.magnitude)
    create_attributes(
        slow_pixel,
        (
            "depends_on",
            "offset",
            "offset_units",
            "transformation_type",
            "units",
            "vector",
        ),
        (
            "/entry/instrument/detector/module/fast_pixel_direction",
            offsets[1],
            "mm",
            "translation",
            format(y_pix.units, "~"),
            slow_axis,
        ),
    )

    # If module_offset is set to 1 or 2, calculate accordinlgy and write the field
    if "module_offset" not in module.keys():
        NXclass_logger.warning(
            "Module_offset option wasn't passed."
            "It will be automatically set to '1' and the origin calculated accordingly."
            "To skip this calculation please set module_offset to '0'."
        )
        module["module_offset"] = "1"

    if module["module_offset"] != "0":
        pixel_size_m = [
            x_pix.magnitude,
            y_pix.magnitude,
        ]
        origin, offset_val = calculate_origin(
            beam_center,
            pixel_size_m,
            fast_axis,
            slow_axis,
            mode=module["module_offset"],
        )
        module_offset = nxmodule.create_dataset("module_offset", data=offset_val)
        create_attributes(
            module_offset,
            (
                "depends_on",
                "offset",
                "offset_units",
                "transformation_type",
                "units",
                "vector",
            ),
            (
                "/entry/instrument/detector/transformations/detector_z/det_z",
                [0, 0, 0],
                "mm",
                "translation",
                format(x_pix.units, "~"),
                origin,
            ),
        )

        # Correct dependency tree accordingly
        _path = "/entry/instrument/detector/module/module_offset"
        create_attributes(fast_pixel, ("depends_on",), (_path,))
        create_attributes(slow_pixel, ("depends_on",), (_path,))


# NXCollection writer (detectorSpecific)
def write_NXcollection(
    nxdetector: h5py.Group,
    detector_params: DetectorType,
    collection_mode: str = "images",
    num_images: int = None,
    meta: Path = None,
):
    """
    Write a NXcollection group inside NXdetector as detectorSpecific.

    Args:
        nxdetector (h5py.Group): HDF5 NXdetector group handle.
        detector_params (DetectorType): Parameters specific to the detector in use.
        collection_mode (str, optional): Data type collected by detector. Defaults to "images".
        num_images (int, optional): Total number of images collected. Defaults to None.
        meta (Path, optional): Path to _meta.h5 file. Defaults to None.
    """
    NXclass_logger.info("Start writing detectorSpecific group as NXcollection.")
    # Create detectorSpecific group
    grp = nxdetector.require_group("detectorSpecific")
    grp.create_dataset("x_pixels", data=detector_params.image_size[1])  # fast axis
    grp.create_dataset("y_pixels", data=detector_params.image_size[0])  # slow axis
    if collection_mode == "images":
        grp.create_dataset("nimages", data=num_images)
    if "software_version" in list(detector_params.constants.keys()):
        if not detector_params.hasMeta or collection_mode == "events":
            grp.create_dataset(
                "software_version",
                data=np.string_(detector_params.constants["software_version"]),
            )
        elif detector_params.hasMeta and meta:
            grp["software_version"] = h5py.ExternalLink(
                meta.name, detector_params.constants["software_version"]
            )
        else:
            grp.create_dataset(
                "software_version",
                data=np.string_(detector_params.constants["software_version"]),
            )
    if "TRISTAN" in detector_params.description.upper():
        tick = ureg.Quantity(detector_params.constants["detector_tick"])
        grp.create_dataset("detector_tick", data=tick.magnitude)
        grp["detector_tick"].attrs["units"] = np.string_(format(tick.units, "~"))
        freq = ureg.Quantity(detector_params.constants["detector_frequency"])
        grp.create_dataset("detector_frequency", data=freq.magnitude)
        grp["detector_frequency"].attrs["units"] = np.string_(format(freq.units, "~"))
        grp.create_dataset(
            "timeslice_rollover_bits",
            data=detector_params.constants["timeslice_rollover"],
        )


# NXdatetime writer
def write_NXdatetime(
    nxsfile: h5py.File,
    timestamp: datetime | str,
    dset_name: TSdset = "start_time",
):
    """Write NX_DATE_TIME fields under /entry/.
    Required fields for NXmx format: 'start_time' and 'end_time_estimated'.
    Optional field: 'end_time', to be writte only if values accurately observed

    Args:
        nxsfile (h5py.File): Nexus file handle.
        timestamp (datetime | str): Timestamp, either in datetime or as a string.
        dset_name (TSdset, optional): NXdatetime dataset name.\
            Allowed values: ["start_time", "end_time", "end_time_estimated". Defaults to "start_time".
    """
    if timestamp is None:
        NXclass_logger.warning(
            f"Timestamp value is None, {dset_name} won't be written."
        )
        return
    nxentry = nxsfile.require_group("entry")
    dset_opts = get_args(TSdset)
    if dset_name not in dset_opts:
        NXclass_logger.warning(
            f"{dset_name} is not an allowed value for NXdatetime dataset. Please pass one of {dset_opts}."
        )
        return
    if type(timestamp) is datetime:
        timestamp = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
    timestamp = get_iso_timestamp(timestamp)
    nxentry.create_dataset(dset_name, data=np.string_(timestamp))


# NXnote writer
# To be used e.g. as a place to store pump-probe info such as pump delay/width
def write_NXnote(nxsfile: h5py.File, loc: str, info: Dict):
    """
    Write any additional information as a NXnote class in a specified location in the NeXus file.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        loc (str): Location inside the NeXus file to write NXnote group.
        info (Dict): Dictionary of datasets to be written to NXnote.
    """
    NXclass_logger.info("Start writing NXnote.")
    # Create the NXnote group in the specified location
    nxnote = nxsfile.require_group(loc)
    create_attributes(
        nxnote,
        ("NX_class",),
        ("NXnote",),
    )

    # Write datasets
    for k, v in info.items():
        if v:  # Just in case one value is not recorded and set as None
            if isinstance(v, str):
                v = np.string_(v)
            nxnote.create_dataset(k, data=v)
            NXclass_logger.info(f"{k} dataset written in {loc}.")


def write_NXcoordinate_system_set(
    nxsfile: h5py.File,
    convention: str,
    base_vectors: Dict[str, Axis],
    origin: List | Tuple | ArrayLike,
):
    """
    Write a container object to store coordinate system conventions different from mcstas.

    The NXcoordinate_system_set base class is used here to define and store the mappings between mcstas and a different coordinate system relevant to the data.
    It should hold at least one NXtransformations group containing a depends_on field, which specifies whether this coordinate system is the reference ("."),
    as well as the three base vectors and the location of the origin.

    A template for base_vectors:
    base_vectors = {"x": (depends_on, transformation_type, units, vector), ...}

    Args:
        nxsfile (h5py.File): Handle to NeXus file.
        convention (str): Convention decription. Defaults to "ED".
        base_vectors (Dict[str, Axis]): The three base vectors of the coordinate system.
        origin (List | Tuple | np.ndarray): The location of the origin of the coordinate system.
    """
    NXclass_logger.info(
        f"Writing NXcoordinate_system_set to define the coordinate system convention for {convention}."
    )

    #
    nxcoord = nxsfile.require_group("/entry/coordinate_system_set")
    create_attributes(
        nxcoord,
        ("NXclass",),
        ("NXcoordinate_system_set",),
    )

    transf = nxcoord.require_group("transformations")
    create_attributes(
        transf,
        ("NXclass",),
        ("NXtransformations",),
    )

    # Needs at least: 3 base vectors, depends_on ("." probably?), origin
    transf.create_dataset("depends_on", data=np.string_("."))  # To be checked
    transf.create_dataset("origin", data=origin)

    # Base vectors
    NXclass_logger.info(
        "Base vectors: \n"
        f"x: {base_vectors['x'].vector} \n"
        f"y: {base_vectors['y'].vector} \n"
        f"z: {base_vectors['z'].vector} \n"
    )
    idx = 0
    for k, v in base_vectors.items():
        base = transf.create_dataset(k, data=np.array(origin[idx]))
        create_attributes(
            base,
            ("depends_on", "transformation_type", "units", "vector"),
            (
                set_dependency(v.depends, transf.name),
                v.transformation_type,
                v.units,
                v.vector,
            ),
        )
        idx += 1
