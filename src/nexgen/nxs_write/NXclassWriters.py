"""
Writer functions for different groups of a NeXus file.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from numpy.typing import ArrayLike

from .. import get_iso_timestamp, units_of_length, units_of_time, ureg
from . import calculate_origin, create_attributes, set_dependency, write_compressed_copy

# from hdf5plugin import Bitshuffle   # noqa: F401


import h5py  # isort: skip


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
    create_attributes(nxentry, ("NX_class", "default"), ("NXentry", "data"))

    # Application definition: /entry/definition
    nxentry.create_dataset("definition", data=np.string_(definition))
    return nxentry


# NXdata writer
def write_NXdata(
    nxsfile: h5py.File,
    datafiles: List[Path],
    goniometer: Dict,
    data_type: Tuple[str, int],
    osc_scan: Dict[str, ArrayLike],
    transl_scan: Dict[str, ArrayLike] = None,
    entry_key: str = "data",
):
    """
    Write NXdata group at /entry/data.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        datafiles (List[Path]): List of Path objects pointing to HDF5 data files.
        goniometer (Dict): Dictionary containing all the axes information.
        data_type (Tuple[str, int]): Images or events.
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
    if data_type[0] == "images":
        tmp_name = f"data_%0{6}d"
        if datafiles[0].parent != Path(nxsfile.filename).parent:
            # This is needed in case the new NeXus file is to be written in a different directory from the data, eg. processing/
            for n, filename in enumerate(datafiles):
                nxdata[tmp_name % (n + 1)] = h5py.ExternalLink(filename, entry_key)
        else:
            for n, filename in enumerate(datafiles):
                nxdata[tmp_name % (n + 1)] = h5py.ExternalLink(filename.name, entry_key)
    elif data_type[0] == "events":
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
    idx = goniometer["axes"].index(osc_axis)
    dep = set_dependency(
        goniometer["depends"][idx], path="/entry/sample/transformations/"
    )

    # Write attributes for axis
    create_attributes(
        ax,
        ("depends_on", "transformation_type", "units", "vector"),
        (
            dep,
            goniometer["types"][idx],
            goniometer["units"][idx],
            goniometer["vectors"][idx],
        ),
    )

    # If present, add linear/grid scan details
    if transl_scan:
        for k, v in transl_scan.items():
            ax_dset = nxdata.create_dataset(k, data=v)
            ax_idx = goniometer["axes"].index(k)
            ax_dep = set_dependency(
                goniometer["depends"][ax_idx], path="/entry/sample/transformations/"
            )
            create_attributes(
                ax_dset,
                ("depends_on", "transformation_type", "units", "vector"),
                (
                    ax_dep,
                    goniometer["types"][ax_idx],
                    goniometer["units"][ax_idx],
                    goniometer["vectors"][ax_idx],
                ),
            )


# NXsample
def write_NXsample(
    nxsfile: h5py.File,
    goniometer: Dict,
    data_type: Tuple[str, int],
    osc_scan: Dict[str, ArrayLike],
    transl_scan: Dict[str, ArrayLike] = None,
    sample_depends_on: str = None,
):
    """
    Write NXsample group at /entry/sample.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        goniometer (Dict):Dictionary containing all the axes information.
        data_type (Tuple[str, int]): Images or events.
        osc_scan (Dict[str, ArrayLike]): Rotation scan. If writing events, this is just a (start, end) tuple.
        transl_scan (Dict[str, ArrayLike], optional): Scan along the xy axes at sample. Defaults to None.
        sample_depends_on (str): Axis on which the sample depends on. If absent, the depends_on field will be set to the last axis listed in the goniometer. Defaults to None.
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
            data=set_dependency(goniometer["axes"][-1], path=nxtransformations.name),
        )

    # Get xy details if passed
    scan_axes = []
    if transl_scan:
        for k in transl_scan.keys():
            scan_axes.append(k)

    # Create sample_{axisname} groups
    for idx, ax in enumerate(goniometer["axes"]):
        grp_name = f"sample_{ax[-1]}" if "sam_" in ax else f"sample_{ax}"
        nxsample_ax = nxsample.create_group(grp_name)
        create_attributes(nxsample_ax, ("NX_class",), ("NXpositioner",))
        if ax == osc_axis:
            # If we're dealing with the scan axis
            if (
                "data" in nxsfile["/entry"].keys()
                and ax in nxsfile["/entry/data"].keys()
            ):
                nxsample_ax[ax] = nxsfile[nxsfile["/entry/data"][ax].name]
                nxtransformations[ax] = nxsfile[nxsfile["/entry/data"][ax].name]
            else:
                nxax = nxsample_ax.create_dataset(ax, data=osc_range)
                _dep = set_dependency(
                    goniometer["depends"][idx], path="/entry/sample/transformations/"
                )
                create_attributes(
                    nxax,
                    ("depends_on", "transformation_type", "units", "vector"),
                    (
                        _dep,
                        goniometer["types"][idx],
                        goniometer["units"][idx],
                        goniometer["vectors"][idx],
                    ),
                )
                nxtransformations[ax] = nxsfile[nxax.name]
            # Write {axisname}_increment_set and {axis_name}_end datasets
            if data_type[0] == "images":
                increment_set = np.repeat(goniometer["increments"][idx], len(osc_range))
                nxsample_ax.create_dataset(
                    ax + "_increment_set",
                    data=goniometer["increments"][idx],
                )  # increment_set
                nxsample_ax.create_dataset(ax + "_end", data=osc_range + increment_set)
        elif ax in scan_axes:
            # For translations
            if (
                "data" in nxsfile["/entry"].keys()
                and ax in nxsfile["/entry/data"].keys()
            ):
                nxsample_ax[ax] = nxsfile[nxsfile["/entry/data"][ax].name]
                nxtransformations[ax] = nxsfile[nxsfile["/entry/data"][ax].name]
            else:
                nxax = nxsample_ax.create_dataset(ax, data=transl_scan[ax])
                _dep = set_dependency(
                    goniometer["depends"][idx], path="/entry/sample/transformations/"
                )
                create_attributes(
                    nxax,
                    ("depends_on", "transformation_type", "units", "vector"),
                    (
                        _dep,
                        goniometer["types"][idx],
                        goniometer["units"][idx],
                        goniometer["vectors"][idx],
                    ),
                )
                nxtransformations[ax] = nxsfile[nxax.name]
        else:
            # For all other axes
            nxax = nxsample_ax.create_dataset(
                ax, data=np.array([goniometer["starts"][idx]])
            )
            _dep = set_dependency(
                goniometer["depends"][idx], path="/entry/sample/transformations/"
            )
            create_attributes(
                nxax,
                ("depends_on", "transformation_type", "units", "vector"),
                (
                    _dep,
                    goniometer["types"][idx],
                    goniometer["units"][idx],
                    goniometer["vectors"][idx],
                ),
            )
            nxtransformations[ax] = nxsfile[nxax.name]

    # Look for nxbeam in file, if it's there make link
    try:
        nxsample["beam"] = nxsfile["/entry/instrument/beam"]
    except KeyError:
        pass


# NXinstrument
def write_NXinstrument(
    nxsfile: h5py.File, beam: Dict, attenuator: Dict, beamline_n: str
):
    """
    Write NXinstrument group at /entry/instrument.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        beam (Dict):Dictionary with beam information, mainly wavelength and flux.
        attenuator (Dict): Dictionary containing transmission.
        beamline_n (str): Identifies which beamline the data was collected on.
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
    NXclass_logger.info(f"DLS beamline {beamline_n}")
    nxinstrument.create_dataset(
        "name", data=np.string_("DIAMOND BEAMLINE " + beamline_n)
    )
    create_attributes(nxinstrument["name"], ("short_name",), ("DLS " + beamline_n,))

    NXclass_logger.info("Write NXattenuator and NXbeam.")
    # Write NXattenuator group: entry/instrument/attenuator
    nxatt = nxinstrument.require_group("attenuator")
    create_attributes(nxatt, ("NX_class",), ("NXattenuator",))
    if attenuator["transmission"]:
        nxatt.create_dataset(
            "attenuator_transmission",
            data=attenuator["transmission"],
        )

    # Write NXbeam group: entry/instrument/beam
    nxbeam = nxinstrument.require_group("beam")
    create_attributes(nxbeam, ("NX_class",), ("NXbeam",))
    wl = nxbeam.create_dataset("incident_wavelength", data=beam["wavelength"])
    create_attributes(wl, ("units",), ("angstrom",))
    if beam["flux"]:
        flux = nxbeam.create_dataset("total_flux", data=beam["flux"])
        create_attributes(flux, ("units"), ("Hz",))


# NXsource
def write_NXsource(nxsfile: h5py.File, source: Dict):
    """
    Write NXsource group /in entry/source.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        source (Dict): Dictionary containing the facility information.
    """
    NXclass_logger.info("Start writing NXsource.")
    nxsource = nxsfile.require_group("/entry/source")
    create_attributes(
        nxsource,
        ("NX_class",),
        ("NXsource",),
    )

    nxsource.create_dataset("name", data=np.string_(source["name"]))
    create_attributes(nxsource["name"], ("short_name",), (source["short_name"],))
    nxsource.create_dataset("type", data=np.string_(source["type"]))
    if "probe" in source.keys():
        nxsource.create_dataset("probe", data=np.string_(source["probe"]))


# NXdetector writer
def write_NXdetector(
    nxsfile: h5py.File,
    detector: Dict,
    data_type: Tuple[str, int],
    meta: Path = None,
    link_list: List = None,
):
    """
    Write_NXdetector group at /entry/instrument/detector.

    Args:
        nxsfile (h5py.File): NeXus file handle.
        detector (Dict): Dictionary containing all detector information.
        data_type (Tuple[str, int]): Images or events.
        meta (Path, optional): Path to _meta.h5 file. Defaults to None.
        link_list (List, optional): List of values from the meta file to be linked instead of copied. Defaults to None.
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
    nxdetector.create_dataset("description", data=np.string_(detector["description"]))
    nxdetector.create_dataset("type", data=np.string_(detector["detector_type"]))

    # If there is a meta file, a lot of information will be linked instead of copied
    if meta and detector["mode"] == "images":
        NXclass_logger.info(f"Found metadata in {meta.as_posix()} file.")
        meta_link = (
            meta.name
            if meta.parent == Path(nxsfile.filename).parent
            else meta.as_posix()
        )
        for ll in link_list[0]:
            nxdetector[ll] = h5py.ExternalLink(meta_link, detector[ll])
    elif detector["mode"] == "events":
        wd = Path(nxsfile.filename).parent
        # Bad pixel mask
        if detector["pixel_mask"]:
            nxdetector.create_dataset(
                "pixel_mask_applied", data=detector["pixel_mask_applied"]
            )
            NXclass_logger.info(
                f"Looking for file {detector['pixel_mask']} in {wd.as_posix()}."
            )
            maskfile = [
                wd / detector["pixel_mask"]
                for f in wd.iterdir()
                if detector["pixel_mask"] == f.name
            ]
            if maskfile:
                NXclass_logger.info("Pixel mask file found in working directory.")
                write_compressed_copy(
                    nxdetector, "pixel_mask", filename=maskfile[0], dset_key="image"
                )
            else:
                NXclass_logger.warning(
                    "No pixel mask file found in working directory."
                    "Writing and ExternalLink."
                )
                mask = Path(detector["pixel_mask"])
                image_key = (
                    "image" if "tristan" in detector["description"].lower() else "/"
                )
                nxdetector["pixel_mask"] = h5py.ExternalLink(mask.name, image_key)
        # Flatfield
        if detector["flatfield"]:
            nxdetector.create_dataset(
                "flatfield_applied", data=detector["flatfield_applied"]
            )
            NXclass_logger.info(
                f"Looking for file {detector['flatfield']} in {wd.as_posix()}."
            )
            flatfieldfile = [
                wd / detector["flatfield"]
                for f in wd.iterdir()
                if detector["flatfield"] == f.name
            ]
            if flatfieldfile:
                NXclass_logger.info("Flatfield file found in working directory.")
                write_compressed_copy(
                    nxdetector, "flatfield", filename=flatfieldfile[0], dset_key="image"
                )
            else:
                NXclass_logger.warning(
                    "No flatfield file found in the working directory."
                    "Writing and ExternalLink."
                )
                flatfield = Path(detector["flatfield"])
                image_key = (
                    "image" if "tristan" in detector["description"].lower() else "/"
                )
                nxdetector["flatfield"] = h5py.ExternalLink(flatfield.name, image_key)
    else:
        # Flatfield
        if type(detector["flatfield"]) is str:
            nxdetector.create_dataset(
                "flatfield_applied", data=detector["flatfield_applied"]
            )
            flatfield = Path(detector["flatfield"])
            nxdetector["flatfield"] = h5py.ExternalLink(flatfield.name, "/")
        elif detector["flatfield"] is None:
            NXclass_logger.warning(
                "No copy of the flatfield has been found, eithere as a file or dataset."
            )
        else:
            nxdetector.create_dataset(
                "flatfield_applied", data=detector["flatfield_applied"]
            )
            write_compressed_copy(nxdetector, "flatfield", data=detector["flatfield"])
        # Bad pixel mask
        if type(detector["pixel_mask"]) is str:
            nxdetector.create_dataset(
                "pixel_mask_applied", data=detector["pixel_mask_applied"]
            )
            mask = Path(detector["pixel_mask"])
            nxdetector["pixel_mask"] = h5py.ExternalLink(mask.name, "/")
        elif detector["pixel_mask"] is None:
            NXclass_logger.warning(
                "No copy of the pixel_mask has been found, eithere as a file or dataset."
            )
        else:
            nxdetector.create_dataset(
                "pixel_mask_applied", data=detector["pixel_mask_applied"]
            )
            write_compressed_copy(nxdetector, "pixel_mask", data=detector["pixel_mask"])

    # Beam center
    # Check that the information hasn't already been written by the meta file.
    if nxdetector.__contains__("beam_center_x") is False:
        beam_center_x = nxdetector.create_dataset(
            "beam_center_x", data=detector["beam_center"][0]
        )
        create_attributes(beam_center_x, ("units",), ("pixels",))
    if nxdetector.__contains__("beam_center_y") is False:
        beam_center_y = nxdetector.create_dataset(
            "beam_center_y", data=detector["beam_center"][1]
        )
        create_attributes(beam_center_y, ("units",), ("pixels",))

    # Pixel size in m
    if nxdetector.__contains__("x_pixel_size") is False:
        x_pix = units_of_length(detector["pixel_size"][0], True)
        x_pix_size = nxdetector.create_dataset("x_pixel_size", data=x_pix.magnitude)
        create_attributes(x_pix_size, ("units",), (format(x_pix.units, "~"),))
    if nxdetector.__contains__("y_pixel_size") is False:
        y_pix = units_of_length(detector["pixel_size"][1], True)
        y_pix_size = nxdetector.create_dataset("y_pixel_size", data=y_pix.magnitude)
        create_attributes(y_pix_size, ("units",), (format(y_pix.units, "~"),))

    # Sensor material, sensor thickness in m
    if nxdetector.__contains__("sensor_material") is False:
        nxdetector.create_dataset(
            "sensor_material", data=np.string_(detector["sensor_material"])
        )
    if nxdetector.__contains__("sensor_thickness") is False:
        sensor_thickness = units_of_length(detector["sensor_thickness"], True)
        nxdetector.create_dataset("sensor_thickness", data=sensor_thickness.magnitude)
        create_attributes(
            nxdetector["sensor_thickness"],
            ("units",),
            (format(sensor_thickness.units, "~"),),
        )

    # Count time
    if detector["exposure_time"]:
        exp_time = units_of_time(detector["exposure_time"])
        nxdetector.create_dataset("count_time", data=exp_time.magnitude)

    # If detector mode is images write overload and underload
    if (
        data_type[0] == "images"
        and nxdetector.__contains__("saturation_value") is False
    ):
        # if detector["overload"] is not None:
        nxdetector.create_dataset("saturation_value", data=detector["overload"])
        nxdetector.create_dataset("underload_value", data=detector["underload"])

    # Write_NXcollection
    write_NXcollection(nxdetector, detector, data_type, meta, link_list)

    # Write NXtransformations: entry/instrument/detector/transformations/detector_z and two_theta
    nxtransformations = nxdetector.require_group("transformations")
    create_attributes(
        nxtransformations,
        ("NX_class",),
        ("NXtransformations",),
    )

    # Create groups for detector_z and any other detector axis (eg. two_theta) if present
    # This assumes that the detector axes are fixed.
    for idx, ax in enumerate(detector["axes"]):
        if ax == "det_z":
            grp_name = "detector_z"
            dist = units_of_length(str(detector["starts"][idx]) + "mm")  # , True)
        else:
            grp_name = ax

        # It shouldn't be too much of an issue but just in case ...
        if detector["depends"][idx] == "det_z":
            grp_dep = "detector_z"
        else:
            grp_dep = detector["depends"][idx]
        _dep = set_dependency(
            detector["depends"][idx],
            nxtransformations.name + f"/{grp_dep}/",
        )

        nxgrp_ax = nxtransformations.create_group(grp_name)
        create_attributes(nxgrp_ax, ("NX_class",), ("NXpositioner",))
        nxdet_ax = nxgrp_ax.create_dataset(ax, data=np.array([detector["starts"][idx]]))
        create_attributes(
            nxdet_ax,
            ("depends_on", "transformation_type", "units", "vector"),
            (
                _dep,
                detector["types"][idx],
                detector["units"][idx],
                detector["vectors"][idx],
            ),
        )
        if ax == detector["axes"][-1]:
            # Detector depends_on
            nxdetector.create_dataset(
                "depends_on",
                data=set_dependency(ax, path=nxgrp_ax.name),
            )

    # Detector distance
    nxdetector.create_dataset("distance", data=dist.magnitude)
    create_attributes(nxdetector["distance"], ("units",), (format(dist.units, "~")))

    # Check if there are any remaining datasets to be written (usually from the meta file but not always)
    others = [
        "threshold_energy",
        "bit_depth_readout",
        "detector_number",
        "detector_readout_time",
        "photon_energy",
    ]
    for dset in others:
        if nxdetector.__contains__(dset) is False and dset in detector.keys():
            val = (
                np.string_(detector[dset])
                if type(detector[dset]) is str
                else detector[dset]
            )
            if val is not None:  # FIXME bit of a gorilla here, for bit_depth_readout
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

    # TODO check how many modules, and write as many, plus NXdetector_group
    nxmodule.create_dataset("data_origin", data=np.array([0, 0]))
    nxmodule.create_dataset("data_size", data=image_size)
    nxmodule.create_dataset("data_stride", data=np.array([1, 1]))

    # Write fast_ and slow_ pixel_direction
    fast_axis = tuple(module["fast_axis"])
    slow_axis = tuple(module["slow_axis"])

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


# NXdetector_group writer
# def writr_NXdetector_group(nxinstrument: h5py.Group, detector: Dict):
# TODO to be added once multiple module functionality works
# pass


# NXCollection writer (detectorSpecific)
def write_NXcollection(
    nxdetector: h5py.Group,
    detector: Dict,
    data_type: Tuple[str, int],
    meta: Path = None,
    link_list: List = None,
):
    """
    Write a NXcollection group inside NXdetector as detectorSpecific.

    Args:
        nxdetector (h5py.Group): HDF5 NXdetector group handle.
        detector (Dict): Dictionary containing all detector information.
        data_type (Tuple[str, int]): Images or events.
        meta (Path, optional): Path to _meta.h5 file. Defaults to None.
        link_list (List, optional): List of values from the meta file to be linked instead of copied. Defaults to None.
    """
    NXclass_logger.info("Start writing detectorSpecific group as NXcollection.")
    # Create detectorSpecific group
    grp = nxdetector.require_group("detectorSpecific")
    grp.create_dataset("x_pixels", data=detector["image_size"][1])  # fast axis
    grp.create_dataset("y_pixels", data=detector["image_size"][0])  # slow axis
    if data_type[0] == "images":
        grp.create_dataset("nimages", data=data_type[1])
    if meta and data_type[0] == "images":
        for l in link_list[1]:
            grp[l] = h5py.ExternalLink(meta.name, detector[l])
    else:
        if "software_version" in detector:
            grp.create_dataset(
                "software_version", data=np.string_(detector["software_version"])
            )
    if "TRISTAN" in detector["description"].upper():  # or data_type[1] == "events":
        tick = ureg.Quantity(detector["detector_tick"])
        grp.create_dataset("detector_tick", data=tick.magnitude)
        grp["detector_tick"].attrs["units"] = format(tick.units, "~")
        freq = ureg.Quantity(detector["detector_frequency"])
        grp.create_dataset("detector_frequency", data=freq.magnitude)
        grp["detector_frequency"].attrs["units"] = format(freq.units, "~")
        grp.create_dataset(
            "timeslice_rollover_bits", data=detector["timeslice_rollover"]
        )


# NXdatetime writer
def write_NXdatetime(nxsfile: h5py.File, timestamps: List | Tuple):
    """
    Write start and end timestamps under /entry/start_time and /entry/end_time.

    Args:
        nxsfile (h5py.File): Nexus file to be written.
        timestamps (List | Tuple): Timestamps (start, end).
    """
    nxentry = nxsfile.require_group("entry")

    start = timestamps[0]
    if start:
        if type(start) is datetime:
            start = start.strftime("%Y-%m-%dT%H:%M:%S")
            start = get_iso_timestamp(start)
        if start.endswith("Z") is False:  # Just in case
            start += "Z"
        nxentry.create_dataset("start_time", data=np.string_(start))

    stop = timestamps[1]
    if stop:
        if type(stop) is datetime:
            stop = stop.strftime("%Y-%m-%dT%H:%M:%S")
            stop = get_iso_timestamp(stop)
        if stop.endswith("Z") is False:
            stop += "Z"
        nxentry.create_dataset("end_time", data=np.string_(stop))


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
            if type(v) is str:
                v = np.string_(v)
            nxnote.create_dataset(k, data=v)
            NXclass_logger.info(f"{k} dataset written in {loc}.")


def write_NXcoordinate_system_set(
    nxsfile: h5py.File,
    convention: str,
    base_vectors: Dict[str, Tuple],
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
        base_vectors (Dict[str, Tuple]): The three base vectors of the coordinate system.
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
        f"x: {base_vectors['x'][-1]} \n"
        f"y: {base_vectors['y'][-1]} \n"
        f"z: {base_vectors['z'][-1]} \n"
    )
    idx = 0
    for k, v in base_vectors.items():
        base = transf.create_dataset(k, data=np.array(origin[idx]))
        create_attributes(
            base,
            ("depends_on", "transformation_type", "units", "vector"),
            (
                set_dependency(v[0], transf.name),
                v[1],
                v[2],
                v[3],
            ),
        )
        idx += 1
