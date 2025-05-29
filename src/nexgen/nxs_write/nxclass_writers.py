"""
Writer functions for different groups of a NeXus file.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, get_args

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
    add_sample_axis_groups,
    calculate_origin,
    create_attributes,
    mask_and_flatfield_writer,
    mask_and_flatfield_writer_for_event_data,
    set_dependency,
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
    nxentry.create_dataset("definition", data=np.bytes_(definition))
    return nxentry


# NXdata writer
def write_NXdata(
    nxsfile: h5py.File,
    datafiles: list[Path],
    data_type: str,
    osc_axis: str = "omega",
    entry_key: str = "data",
):
    """
    Write NXdata group at /entry/data.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        datafiles (list[Path]): List of Path objects pointing to HDF5 data files.
        data_type (str): Images or events.
        osc_scan (str, optional): Rotation scan axis name. Defaults to omega.
        entry_key (str): Entry key to create the external links to the data files. Defaults to data.

    Raises:
        OSError: If no data is passed.
        ValueError: If the data type is neither "images" nor "events".
    """
    NXclass_logger.debug("Start writing NXdata.")
    # Check that a valid datafile_list has been passed.
    if len(datafiles) == 0:
        raise OSError(
            "No HDF5 data filenames have been found. Please pass at least one."
        )

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


# NXtransformations
def write_NXtransformations(
    parent_group: h5py.Group,
    axes: list[Axis],
    scan: Optional[dict[str, ArrayLike]] = None,
    collection_type: str = "images",
):
    """Write NXtransformations group.

    This group coulld be written either in /entry/sample/ for the goniometer or in \
    /entry/instrument/detector for the detector axes. In the latter case, the scan \
    should always be None.

    Args:
        parent_group (h5py.Group): Handle to HDF5 group where NXtransformations \
            should be written.
        axes (list[Axis]): list of Axes to write to the NXtransformations group.
        scan (Optional[dict[str, ArrayLike]], optional): All the scan axes, both \
            rotation and translation. Defaults to None.
        collection_type (str, optional): Collection type, could be images or \
            events. Defaults to "images".
    """
    NXclass_logger.debug(f"Start writing NXtransformations group in {parent_group}.")
    nxtransformations = parent_group.require_group("transformations")
    create_attributes(
        nxtransformations,
        ("NX_class",),
        ("NXtransformations",),
    )

    for ax in axes:
        # Dataset
        data = (
            scan[ax.name]
            if scan and ax.name in scan.keys()
            else np.array([ax.start_pos])
        )
        # Dependency
        ax_dep = set_dependency(ax.depends, path=nxtransformations.name)

        nxax = nxtransformations.create_dataset(ax.name, data=data)
        create_attributes(
            nxax,
            ("depends_on", "transformation_type", "units", "vector"),
            (ax_dep, ax.transformation_type, ax.units, ax.vector),
        )

        # Write _increment_set and _end for rotation axis
        if scan and collection_type == "images":
            if ax.name in scan.keys() and ax.transformation_type == "rotation":
                NXclass_logger.debug(
                    f"Adding increment_set and end for axis {ax.name}."
                )
                nxtransformations.create_dataset(
                    f"{ax.name}_increment_set", data=ax.increment
                )
                increment_set = np.repeat(ax.increment, len(scan[ax.name]))
                ax_end = scan[ax.name] + increment_set
                nxtransformations.create_dataset(f"{ax.name}_end", data=ax_end)


# NXsample
def write_NXsample(
    nxsfile: h5py.File,
    goniometer_axes: list[Axis],
    data_type: str,
    osc_scan: dict[str, ArrayLike],
    transl_scan: dict[str, ArrayLike] = None,
    sample_depends_on: str = None,
    sample_details: dict[str, Any] = None,
    add_nonstandard_fields: bool = True,
):
    """
    Write NXsample group at /entry/sample.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        goniometer_axes (list[Axis]): List of goniometer axes.
        data_type (str): Images or events.
        osc_scan (dict[str, ArrayLike]): Rotation scan. If writing events, this is just a (start, end) tuple.
        transl_scan (dict[str, ArrayLike], optional): Scan along the xy axes at sample. Defaults to None.
        sample_depends_on (str, optional): Axis on which the sample depends on. If absent, the depends_on field \
            will be set to the last axis listed in the goniometer. Defaults to None.
        sample_details (dict[str, Any], optional): General information about the sample, eg. name, temperature.
        add_nonstandard_fields (bool, optional): Choose whether to add the old "sample_{x,phi,...}/{x,phi,...}" to the group. \
            These fields are non-standard but may be needed for processing to run. Defaults to True.
    """
    NXclass_logger.debug("Start writing NXsample.")
    # Create NXsample group, unless it already exists, in which case just open it.
    nxsample = nxsfile.require_group("/entry/sample")
    create_attributes(
        nxsample,
        ("NX_class",),
        ("NXsample",),
    )

    # Merge the scan dictionaries
    full_scan = osc_scan if transl_scan is None else osc_scan | transl_scan

    # Create NXtransformations group: /entry/sample/transformations
    write_NXtransformations(nxsample, goniometer_axes, full_scan, data_type)
    if add_nonstandard_fields:
        add_sample_axis_groups(nxsample, goniometer_axes)

    # Save sample depends_on
    if sample_depends_on:
        nxsample.create_dataset(
            "depends_on",
            data=set_dependency(
                sample_depends_on, path=nxsample["transformations"].name
            ),
        )
    else:
        nxsample.create_dataset(
            "depends_on",
            data=set_dependency(
                goniometer_axes[-1].name, path=nxsample["transformations"].name
            ),
        )

    # Add scan axes datasets to NXdata
    nxdata = nxsfile.require_group("/entry/data")
    for ax in goniometer_axes:
        if ax.name in full_scan.keys():
            nxdata[ax.name] = nxsfile[f"/entry/sample/transformations/{ax.name}"]

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
                v = np.bytes_(v)
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
        beam (dict): dictionary with beam information, mainly wavelength and flux.
        attenuator (dict): Dictionary containing transmission.
        source (Source): Source definition, containing the facility information.
        reset_instrument_name (bool, optional): If True, a string with the name of the \
            instrument used. Otherwise, it will be set to 'DIAMOND BEAMLINE Ixx'. Defaults to False.
    """
    NXclass_logger.debug("Start writing NXinstrument.")
    # Create NXinstrument group, unless it already exists, in which case just open it.
    nxinstrument = nxsfile.require_group("/entry/instrument")
    create_attributes(
        nxinstrument,
        ("NX_class",),
        ("NXinstrument",),
    )

    # Write /name field and relative attribute
    NXclass_logger.debug(f"{source.facility.short_name} {source.beamline}")
    name_str = (
        source.set_instrument_name
        if reset_instrument_name
        else f"DIAMOND BEAMLINE {source.beamline}"
    )
    nxinstrument.create_dataset("name", data=np.bytes_(name_str))
    create_attributes(
        nxinstrument["name"],
        ("short_name",),
        (f"{source.facility.short_name} {source.beamline}",),
    )

    NXclass_logger.debug("Write NXattenuator and NXbeam.")
    # Write NXattenuator group: entry/instrument/attenuator
    write_NXattenuator(nxinstrument, attenuator)
    # Write NXbeam group: entry/instrument/beam
    write_NXbeam(nxinstrument, beam)


def write_NXattenuator(nxinstrument: h5py.Group, attenuator: Attenuator):
    """Write the NXattenuator group in /entry/instrument/attenuator.

    Args:
        nxinstrument (h5py.Group): HDF5 Nxinstrument group handle.
        attenuator (Attenuator):  Attenuator definition, with transmission.
    """
    nxatt = nxinstrument.require_group("attenuator")
    create_attributes(nxatt, ("NX_class",), ("NXattenuator",))
    if attenuator.transmission:
        nxatt.create_dataset(
            "attenuator_transmission",
            data=attenuator.transmission,
        )


def write_NXbeam(nxinstrument: h5py.Group, beam: Beam):
    """Write the NXbeam group in /entry/instrument/beam.

    Args:
        nxinstrument (h5py.Group): HDF5 Nxinstrument group handle.
        beam (Beam):  Beam definition with wavelength and flux.
    """
    nxbeam = nxinstrument.require_group("beam")
    create_attributes(nxbeam, ("NX_class",), ("NXbeam",))
    _wavelength = (
        beam.wavelength
        if not isinstance(beam.wavelength, list)
        else np.array(beam.wavelength)
    )
    wl = nxbeam.create_dataset("incident_wavelength", data=_wavelength)
    create_attributes(wl, ("units",), ("angstrom",))
    if isinstance(beam.wavelength, list) and beam.wavelength_weights:
        if len(beam.wavelength) != len(beam.wavelength_weights):
            msg = "Cannot write wavelength weights dataset as length doesn't match number of wavelengths."
            NXclass_logger.error(msg)
            raise ValueError(msg)
        nxbeam.create_dataset(
            "incident_wavelength_weights", data=np.array(beam.wavelength_weights)
        )

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
    NXclass_logger.debug("Start writing NXsource.")
    nxsource = nxsfile.require_group("/entry/source")
    create_attributes(
        nxsource,
        ("NX_class",),
        ("NXsource",),
    )

    nxsource.create_dataset("name", data=np.bytes_(source.facility.name))
    create_attributes(nxsource["name"], ("short_name",), (source.facility.short_name,))
    nxsource.create_dataset("type", data=np.bytes_(source.facility.type))
    if source.probe:
        nxsource.create_dataset("probe", data=np.bytes_(source.probe))


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
    NXclass_logger.debug("Start writing NXdetector.")
    # Create NXdetector group, unless it already exists, in which case just open it.
    nxdetector = nxsfile.require_group("/entry/instrument/detector")
    create_attributes(
        nxdetector,
        ("NX_class",),
        ("NXdetector",),
    )

    # Detector description
    nxdetector.create_dataset(
        "description", data=np.bytes_(detector.detector_params.description)
    )
    nxdetector.create_dataset(
        "type", data=np.bytes_(detector.detector_params.detector_type)
    )

    collection_mode = detector.get_detector_mode()

    # If there is a meta file, a lot of information will be linked instead of copied
    if isinstance(detector.detector_params, EigerDetector):
        if meta:
            NXclass_logger.debug(f"Found metadata in {meta.as_posix()} file.")
            meta_link = (
                meta.name
                if meta.parent == Path(nxsfile.filename).parent
                else meta.as_posix()
            )
            for k, v in detector.detector_params.constants.items():
                if k in [
                    "software_version",
                    "ntrigger",
                    "data_collection_date",
                    "eiger_fw_version",
                    "serial_number",
                ]:
                    # NOTE: Software version, eiger_fw_version ntrigger & date should
                    # go in detectorSpecific (NXcollection)
                    continue
                nxdetector[k] = h5py.ExternalLink(meta_link, v)
        else:
            NXclass_logger.warning(
                """
                Meta file for Eiger detector hasn't been specified or found.
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
            mask_and_flatfield_writer_for_event_data(
                nxdetector,
                "pixel_mask",
                pixel_mask_file,
                detector.detector_params.constants["pixel_mask_applied"],
                wd,
                detector.detector_params.description.lower(),
            )
            # Flatfield
            mask_and_flatfield_writer_for_event_data(
                nxdetector,
                "flatfield",
                flatfield_file,
                detector.detector_params.constants["flatfield_applied"],
                wd,
                detector.detector_params.description.lower(),
            )
        else:
            # Flatfield
            mask_and_flatfield_writer(
                nxdetector,
                "flatfield",
                detector.detector_params.constants["flatfield"],
                detector.detector_params.constants["flatfield_applied"],
            )
            # Bad pixel mask
            mask_and_flatfield_writer(
                nxdetector,
                "pixel_mask",
                detector.detector_params.constants["pixel_mask"],
                detector.detector_params.constants["pixel_mask_applied"],
            )

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
        "sensor_material", data=np.bytes_(detector.detector_params.sensor_material)
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
    create_attributes(
        nxdetector["count_time"], ("units",), (format(exp_time.units, "~"),)
    )

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
    write_NXtransformations(nxdetector, detector.detector_axes)
    # NXdetector depends on the last (often only) axis in the list
    det_dep = set_dependency(
        detector.detector_axes[-1].name,
        path="/entry/instrument/detector/transformations",
    )
    nxdetector.create_dataset("depends_on", data=det_dep)

    # Just a det_z check
    if "det_z" not in list(nxdetector["transformations"].keys()):
        NXclass_logger.error("No det_z field in nexus file.")
        return

    # Write a soft link for detector_z, workaround for autoPROC
    # TODO see https://github.com/DiamondLightSource/nexgen/issues/140
    nxdetector.create_group("detector_z")
    create_attributes(
        nxdetector["detector_z"],
        ("NX_class",),
        ("NXtransformations",),  # NXtransformations instead of NXpositioner. TOBETESTED
    )
    nxdetector["detector_z/det_z"] = nxsfile[
        "/entry/instrument/detector/transformations/det_z"
    ]

    # Detector distance
    det_z_idx = [
        n for n, ax in enumerate(detector.detector_axes) if ax.name == "det_z"
    ][0]
    dist = units_of_length(str(detector.detector_axes[det_z_idx].start_pos) + "mm")

    nxdetector.create_dataset("distance", data=dist.to("m").magnitude)
    create_attributes(
        nxdetector["distance"], ("units",), (format(dist.to("m").units, "~"))
    )


# NXdetector_module writer
def write_NXdetector_module(
    nxsfile: h5py.File,
    module: dict,
    image_size: list | tuple,
    pixel_size: list | tuple,
    beam_center: Optional[list | tuple] = None,
):
    """
    Write NXdetector_module group at /entry/instrument/detector/module.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        module (dict): Dictionary containing the detector module information: fast and slow axes, how many modules.
        image_size (list | tuple): Size of the detector, in pixels, passed in the order (slow, fast) axis.
        pixel_size (list | tuple): Size of the single pixels in fast and slow direction, in mm.
        beam_center (Optional[list | tuple], optional): Beam center position, needed only if origin needs to be calculated. Defaults to None.
    """
    NXclass_logger.debug("Start writing NXdetector_module.")
    # Create NXdetector_module group, unless it already exists, in which case just open it.
    nxmodule = nxsfile.require_group("/entry/instrument/detector/module")
    create_attributes(
        nxmodule,
        ("NX_class",),
        ("NXdetector_module",),
    )

    nxmodule.create_dataset("data_origin", data=np.array([0, 0]), dtype=np.uint32)
    nxmodule.create_dataset("data_size", data=image_size, dtype=np.uint32)
    nxmodule.create_dataset("data_stride", data=np.array([1, 1]), dtype=np.uint32)

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
            "/entry/instrument/detector/transformations/det_z",
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
                "/entry/instrument/detector/transformations/det_z",
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
    NXclass_logger.debug("Start writing detectorSpecific group as NXcollection.")
    # Create detectorSpecific group
    grp = nxdetector.require_group("detectorSpecific")
    grp.create_dataset(
        "x_pixels", data=detector_params.image_size[1], dtype=np.uint32
    )  # fast axis
    grp.create_dataset(
        "y_pixels", data=detector_params.image_size[0], dtype=np.uint32
    )  # slow axis
    # Write these non-spec fields as well because of autoPROC:
    grp.create_dataset(
        "x_pixels_in_detector", data=detector_params.image_size[1], dtype=np.uint32
    )  # fast axis
    grp.create_dataset(
        "y_pixels_in_detector", data=detector_params.image_size[0], dtype=np.uint32
    )  # slow axis
    if collection_mode == "images":
        grp.create_dataset("nimages", data=num_images)
    if "software_version" in list(detector_params.constants.keys()):
        if not detector_params.hasMeta or collection_mode == "events":
            grp.create_dataset(
                "software_version",
                data=np.bytes_(detector_params.constants["software_version"]),
            )
        elif detector_params.hasMeta and meta:
            grp["software_version"] = h5py.ExternalLink(
                meta.name, detector_params.constants["software_version"]
            )
        else:
            grp.create_dataset(
                "software_version",
                data=np.bytes_(detector_params.constants["software_version"]),
            )
    if "EIGER" in detector_params.description.upper() and meta:
        for field in ["ntrigger"]:  # , "data_collection_date", "eiger_fw_version"]:
            grp[field] = h5py.ExternalLink(meta.name, detector_params.constants[field])
    elif "TRISTAN" in detector_params.description.upper():
        tick = ureg.Quantity(detector_params.constants["detector_tick"])
        grp.create_dataset("detector_tick", data=tick.magnitude)
        grp["detector_tick"].attrs["units"] = np.bytes_(format(tick.units, "~"))
        freq = ureg.Quantity(detector_params.constants["detector_frequency"])
        grp.create_dataset("detector_frequency", data=freq.magnitude)
        grp["detector_frequency"].attrs["units"] = np.bytes_(format(freq.units, "~"))
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
    nxentry.create_dataset(dset_name, data=np.bytes_(timestamp))


# NXnote writer
# To be used e.g. as a place to store pump-probe info such as pump delay/width
def write_NXnote(nxsfile: h5py.File, loc: str, info: dict):
    """
    Write any additional information as a NXnote class in a specified location in the NeXus file.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        loc (str): Location inside the NeXus file to write NXnote group.
        info (dict): Dictionary of datasets to be written to NXnote.
    """
    NXclass_logger.debug("Start writing NXnote.")
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
                v = np.bytes_(v)
            nxnote.create_dataset(k, data=v)
            NXclass_logger.debug(f"{k} dataset written in {loc}.")


def write_NXcoordinate_system_set(
    nxsfile: h5py.File,
    convention: str,
    base_vectors: dict[str, Axis],
    origin: list | tuple | ArrayLike,
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
        base_vectors (dict[str, Axis]): The three base vectors of the coordinate system.
        origin (list | tuple | np.ndarray): The location of the origin of the coordinate system.
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
    transf.create_dataset("depends_on", data=np.bytes_("."))  # To be checked
    transf.create_dataset("origin", data=origin)

    # Base vectors
    NXclass_logger.debug(
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
