#!/usr/bin/env python

"""
This program is used to create example NeXus files using metadata from an input .json file.

Example:
    python writer.py output_nexus.h5 input_metadata.json
    python writer.py output_nexus.nxs input_metadata.json

A custom .json file containing metadata can be created by modifying and running create_metadata.py.
"""
import os
import numpy
import h5py
from hdf5plugin import Bitshuffle

from . import imgcif2mcstas, create_attributes, set_dependency


def generate_image_data(shape, filename):
    # data = numpy.ndarray(shape)
    # data.fill(0)
    with h5py.File(filename, "w") as datafile:
        datafile.create_dataset(
            "data",
            shape=shape,
            dtype="i4",
            chunks=(1, shape[1], shape[2]),
            **Bitshuffle(),
        )


# TODO add only link to files in nxdata
def generate_event_data(num_events, outfile):
    outfile.create_dataset("cue_id", data=numpy.zeros(100), **Bitshuffle())
    outfile.create_dataset("cue_timestamp_zero", data=numpy.zeros(100), **Bitshuffle())
    outfile.create_dataset("event_id", data=numpy.zeros(num_events), **Bitshuffle())
    outfile.create_dataset(
        "event_time_offset", data=numpy.zeros(num_events), **Bitshuffle()
    )
    outfile.create_dataset("event_energy", data=numpy.zeros(num_events), **Bitshuffle())


class NexusWriter:
    """
    Class to write metadata in NeXus file.
    """

    def __init__(self, nxsfile: h5py.File, params):
        self._params = params
        # Define coordinate frame
        self._cf = params.input.coordinate_frame

        # Output parameters
        self._nxs = nxsfile
        self._datafile = params.output.data_file_template

        # Unpack input parameters
        self.goniometer = params.input.goniometer
        self.detector = params.input.detector
        self.attenuator = params.input.attenuator
        self.beam = params.input.beam
        self.beamline = params.input.beamline

        # Which kind of data is being generated?
        self._mode = self.detector.mode

    @staticmethod
    def split_arrays(coord_frame, _axes, _array):
        # If coordinate frame is imgcif conver and make a list of arrays
        # else just split into a list
        v = []
        for j in range(len(_axes)):
            a = _array[3 * j : 3 * j + 3]
            if coord_frame == "imgcif":
                v.append(imgcif2mcstas(a))
                # print("Converting to mcstas coordinates ...")
            else:
                v.append(a)
        return v

    @staticmethod
    def calculate_module_offset(
        beam_center_xy, xy_pixel_size, fast_axis_v, slow_axis_v
    ):
        # assumes fast and slow axis vectors have already been converted if needed
        # Scaled center
        x_scaled = beam_center_xy[0] * xy_pixel_size[0]
        y_scaled = beam_center_xy[1] * xy_pixel_size[1]
        # Detector origin
        det_origin = x_scaled * numpy.array(fast_axis_v) + y_scaled * numpy.array(
            slow_axis_v
        )
        det_origin = list(-det_origin)
        return det_origin

    def write_NXdata(self, nxentry):
        # Find scan axis
        goniometer = self.goniometer
        # Scan axis is the on that has a different start and end value
        # idx = numpy.where(goniometer.starts != goniometer.ends)[0][0]
        # FIXME for some reason this returns the wrong index
        idx = [(i != j) for i, j in zip(goniometer.starts, goniometer.ends)].index(
            True
        )  # TEMPORARY FIX

        nxdata = nxentry.create_group("data")
        create_attributes(
            nxdata,
            ("NX_class", "axes", "signal"),
            ("NXdata", goniometer.axes[idx], "data"),
        )

        # If mode = images, create blank image data, else go to events
        if self._mode == "images":
            # TODO FIX THIS GORILLA
            if self._params.input.n_images:
                dset_shape = (self._params.input.n_images,) + tuple(
                    self.detector.image_size
                )
                _scan_range = numpy.linspace(
                    goniometer.starts[idx],
                    goniometer.ends[idx],
                    self._params.input.n_images,
                )
            else:
                _scan_range = numpy.arange(
                    goniometer.starts[idx],
                    goniometer.ends[idx],
                    goniometer.increments[idx],
                )
                dset_shape = (len(_scan_range),) + tuple(self.detector.image_size)

            generate_image_data(dset_shape, self._datafile)
            nxdata["datafile"] = h5py.ExternalLink(self._datafile, "data")
        else:
            # TODO This needs some serious rethinking at some point
            dirname = os.path.dirname(self._nxs.filename)
            outfile = os.path.join(dirname, "File_00000{}.h5")
            _scan_range = (goniometer.starts[idx], goniometer.ends[idx])
            # Let's make 2 files of event data
            for n in range(1, 3):
                with h5py.File(outfile.format(n), "w") as out:
                    generate_event_data(self._params.input.n_events, out)
                    nxdata["File_00000{}".format(n)] = h5py.ExternalLink(
                        out.filename, "/"
                    )

        # TODO handle stills
        ax = nxdata.create_dataset(goniometer.axes[idx], data=_scan_range)
        _dep = set_dependency(
            goniometer.depends[idx], path="/entry/sample/transformations/"
        )
        # This could probably be handled better but for the moment it works
        # if self._cf == "imgcif":
        #    _vector = imgcif2mcstas(goniometer.vector[idx])
        # else:
        #    _vector = goniometer.vectors[idx]
        vectors = NexusWriter.split_arrays(
            self._cf, goniometer.axes, goniometer.vectors
        )
        create_attributes(
            ax,
            ("depends_on", "transformation_type", "units", "vector"),
            (
                _dep,
                goniometer.types[idx],
                goniometer.units[idx],
                vectors[idx],
                # _vector,
            ),
        )

    def write_NXdetector(self, nxinstr):
        detector = self.detector
        nxdet = nxinstr.create_group("detector")
        create_attributes(nxdet, ("NX_class",), ("NXdetector",))
        nxdet.create_dataset(
            "depends_on", data="/entry/instrument/transformations/det_z"
        )
        # Detector description
        nxdet.create_dataset("description", data=numpy.string_(detector.description))
        nxdet.create_dataset("type", data=numpy.string_("Pixel"))

        # Beam center
        beam_center_x = nxdet.create_dataset(
            "beam_center_x", data=detector.beam_center[0]
        )
        create_attributes(beam_center_x, ("units",), ("pixels",))
        beam_center_y = nxdet.create_dataset(
            "beam_center_y", data=detector.beam_center[1]
        )
        create_attributes(beam_center_y, ("units",), ("pixels",))

        # Pixel size
        x_pix_size = nxdet.create_dataset(
            "x_pixel_size", data=detector.pixel_size[0] / 1000
        )
        create_attributes(x_pix_size, ("units",), ("m",))
        y_pix_size = nxdet.create_dataset(
            "y_pixel_size", data=detector.pixel_size[1] / 1000
        )
        create_attributes(y_pix_size, ("units",), ("m",))

        # Count time
        nxdet.create_dataset("count_time", data=detector.exposure_time)

        # Sensor material, sensor thickness
        nxdet.create_dataset(
            "sensor_material", data=numpy.string_(detector.sensor_material)
        )
        nxdet.create_dataset("sensor_thickness", data=detector.sensor_thickness / 1000)
        create_attributes(nxdet["sensor_thickness"], ("units",), ("m",))

        if self._mode == "images":
            # Overload and underload
            nxdet.create_dataset("saturation_value", data=detector.overload)
            nxdet.create_dataset("underload_value", data=detector.underload)

        # Flatfield
        if detector.flatfield:
            nxdet.create_dataset("flatfield_applied", data=False)
            nxdet.create_dataset(
                "flatfield", data="ExternalLink/to/flatfield/correction/data"
            )
        # Bad pixel mask
        if detector.pixel_mask:
            nxdet.create_dataset("pixel_mask_applied", data=False)
            nxdet.create_dataset(
                "pixel_mask", data="ExternalLink/to/mask/correction/data"
            )

        # Module: /entry/instrument/detector/module
        self.write_NXdetector_module(nxdet)

        # DetectorSpecific: /entry/instrument/detector/detectorSpecific
        self.write_NXdetectorSpec(nxdet)

    def write_NXdetector_module(self, nxdet):
        detector = self.detector
        nxmod = nxdet.create_group("module")
        create_attributes(nxmod, ("NX_class",), ("NXdetector_module",))
        nxmod.create_dataset("data_origin", data=numpy.array([0, 0]))
        nxmod.create_dataset("data_size", data=detector.image_size)
        nxmod.create_dataset("data_stride", data=numpy.array([1, 1]))

        if self._cf == "imgcif":
            fast_axis = imgcif2mcstas(detector.fast_axis)
            slow_axis = imgcif2mcstas(detector.slow_axis)
        else:
            fast_axis = detector.fast_axis
            slow_axis = detector.slow_axis

        offsets = NexusWriter.split_arrays(self._cf, ["fast", "slow"], detector.offsets)
        # TODO this needs some rethinking

        # Fast/slow pixel direction
        fast_pixel = nxmod.create_dataset(
            "fast_pixel_direction", data=detector.pixel_size[0] / 1000
        )
        create_attributes(
            fast_pixel,
            ("depends_on", "offset", "transformation_type", "units", "vector"),
            (
                "/entry/instrument/transformations/det_z",
                offsets[0],
                "translation",
                "m",
                fast_axis,
            ),
        )
        slow_pixel = nxmod.create_dataset(
            "slow_pixel_direction", data=detector.pixel_size[1] / 1000
        )
        create_attributes(
            slow_pixel,
            ("depends_on", "offset", "transformation_type", "units", "vector"),
            (
                "/entry/instrument/detector/module/fast_pixel_direction",
                offsets[1],
                "translation",
                "m",
                slow_axis,
            ),
        )
        # Module_offset
        if detector.module_offset is True:
            offset = NexusWriter.calculate_module_offset(
                detector.beam_center, detector.pixel_size, fast_axis, slow_axis
            )
            module_offset = nxmod.create_dataset("module_offset", data=([0.0]))
            create_attributes(
                module_offset,
                ("depends_on", "offset", "transformation_type", "units", "vector"),
                (
                    "/entry/instrument/transformations/det_z",
                    offset,
                    "translation",
                    "m",
                    [1, 0, 0],
                ),
            )
            # Set correct path for deendency of fast and slow axis
            _path = "/entry/instrument/detector/module/module_offset"
            create_attributes(fast_pixel, ("depends_on"), (_path,))
            create_attributes(slow_pixel, ("depends_on"), (_path,))

    def write_NXdetectorSpec(self, nxdet):
        detector = self.detector
        grp = nxdet.create_group("detectorSpecific")
        grp.create_dataset("x_pixels", data=detector.image_size[0])
        grp.create_dataset("y_pixels", data=detector.image_size[1])
        # TODO add this again
        # if self._mode == "images":
        #    grp.create_dataset("nimages", data=self._params.input.n_images)

    def write_NXpositioner(self, nxinstr):
        detector = self.detector
        vectors = NexusWriter.split_arrays(self._cf, detector.axes, detector.vectors)

        # Detector_z: /entry/instrument/detector_z
        assert "det_z" in detector.axes, "detector_z not in metadata"
        idx = detector.axes.index("det_z")
        nxdet_z = nxinstr.create_group("detector_z")
        create_attributes(nxdet_z, ("NX_class",), ("NXpositioner",))
        det_z = nxdet_z.create_dataset(detector.axes[idx], data=detector.starts[idx])
        _dep = set_dependency(
            detector.depends[idx], "/entry/instrument/transformations/"
        )
        create_attributes(
            det_z,
            ("depends_on", "transformation_type", "units", "vector"),
            (
                _dep,
                detector.types[idx],
                detector.units[idx],
                vectors[idx],
            ),
        )

        # Transformations: /entry/instrument/transformations
        nxtransf = nxinstr.create_group("transformations")
        create_attributes(nxtransf, ("NX_class",), ("NXtransformations",))
        _link = "/entry/instrument/detector_z/" + detector.axes[idx]
        nxtransf["det_z"] = self._nxs[_link]

        # Add two_theta arm
        if "two_theta" in detector.axes:
            i = detector.axes.index("two_theta")
            twotheta = nxtransf.create_dataset(
                detector.axes[i], data=detector.starts[i]
            )
            _dep = set_dependency(
                detector.depends[i],
                "/entry/instrument/transformations/",
            )
            create_attributes(
                twotheta,
                ("depends_on", "transformation_type", "units", "vector"),
                (
                    _dep,
                    detector.types[i],
                    detector.units[i],
                    vectors[i],
                ),
            )

            nx2theta = nxinstr.create_group("twotheta")
            create_attributes(nx2theta, ("NX_class",), ("NXpositioner",))
            nx2theta["two_theta"] = self._nxs[
                "/entry/instrument/transformations/two_theta"
            ]

    def write_NXinstrument(self, nxentry):
        nxinstr = nxentry.create_group("instrument")
        create_attributes(
            nxinstr, ("NX_class", "short_name"), ("NXinstrument", "beamline")
        )

        # NXattenuator: /entry/instrument/attenuator
        attenuator = self.attenuator
        nxatt = nxinstr.create_group("attenuator")
        create_attributes(nxatt, ("NX_class",), ("NXattenuator",))
        nxatt.create_dataset(
            "attenuator_transmission",
            data=attenuator.transmission,
        )

        # NXbeam: /entry/instrument/beam
        beam = self.beam
        nxbeam = nxinstr.create_group("beam")
        create_attributes(nxbeam, ("NX_class",), ("NXbeam",))
        wl = nxbeam.create_dataset("incident_wavelength", data=beam.wavelength)
        create_attributes(wl, ("units",), ("angstrom",))
        flux = nxbeam.create_dataset("total_flux", data=beam.flux)
        create_attributes(flux, ("units"), ("Hz",))

        # NXsource: /entry/instrument/source
        source = self.beamline.source
        nxsource = nxinstr.create_group("source")
        create_attributes(nxsource, ("NX_class",), ("NXsource",))
        nxsource.create_dataset("name", data=numpy.string_(source.name))
        create_attributes(nxsource["name"], ("short_name",), (source.short_name,))
        nxsource.create_dataset("type", data=numpy.string_(source.type))

        # NXdetector: /entry/instrument/detector
        self.write_NXdetector(nxinstr)

        # NXpositioner: /entry/instrument/detector_z, /entry/instrument/transformations
        self.write_NXpositioner(nxinstr)

    def write_NXsample(self, nxentry):
        goniometer = self.goniometer
        nxsample = nxentry.create_group("sample")
        create_attributes(nxsample, ("NX_class",), ("NXsample",))
        # Sample depends_on
        nxsample.create_dataset(
            "depends_on",
            data=set_dependency(
                goniometer.axes[-1], path="/entry/sample/transformations/"
            ),
        )
        # Beam: /entry/sample/beam
        nxsample["beam"] = self._nxs["/entry/instrument/beam"]

        # Transformations: /entry/sample/transformations
        nxtr = nxsample.create_group("transformations")
        create_attributes(nxtr, ("NX_class",), ("NXtransformations",))

        # Get a list of axis vectors
        vectors = NexusWriter.split_arrays(
            self._cf, goniometer.axes, goniometer.vectors
        )

        # Axes: /entry/sample/sample_
        # idx = numpy.where(goniometer.starts != goniometer.ends)[0][0]
        idx = [(i != j) for i, j in zip(goniometer.starts, goniometer.ends)].index(
            True
        )  # TEMPORARY FIX p2
        scan_axis = goniometer.axes[idx]
        for k in range(len(goniometer.axes)):
            if goniometer.axes[k] == scan_axis:
                nxscan = nxsample.create_group("sample_" + scan_axis)
                create_attributes(nxscan, ("NX_class",), ("NXpositioner",))
                nxscan[scan_axis] = self._nxs["/entry/data/" + scan_axis]
                nxtr[scan_axis] = self._nxs[
                    "/entry/sample/sample_" + scan_axis + "/" + scan_axis
                ]
            else:
                if "sam" in goniometer.axes[k]:
                    grp = "sample_" + goniometer.axes[k].split("_")[1]
                else:
                    grp = "sample_" + goniometer.axes[k]
                nxax = nxsample.create_group(grp)
                create_attributes(nxax, ("NX_class",), ("NXpositioner",))
                ax = nxax.create_dataset(goniometer.axes[k], data=goniometer.starts[k])
                _dep = set_dependency(
                    goniometer.depends[k], path="/entry/sample/transformations/"
                )
                create_attributes(
                    ax,
                    ("depends_on", "transformation_type", "units", "vector"),
                    (
                        _dep,
                        goniometer.types[k],
                        goniometer.units[k],
                        vectors[k],
                    ),
                )
                nxtr[goniometer.axes[k]] = self._nxs[
                    "/entry/sample/" + grp + "/" + goniometer.axes[k]
                ]

    def write(self):
        # Start writing the NeXus tree
        nxentry = self._nxs.create_group("entry")
        create_attributes(nxentry, ("NX_class",), ("NXentry",))

        # Definition: /entry/definition
        nxentry.create_dataset("definition", data=numpy.string_("NXmx"))

        # Data: /entry/data
        self.write_NXdata(nxentry)

        # Instrument: /entry/instrument
        self.write_NXinstrument(nxentry)

        # Sample: /entry/sample
        self.write_NXsample(nxentry)

        # Start and end time: /entry/start_time, /entry/end_time
        # Type: NX_DATE_TIME.
        # Start_time: time of collection first data point
        # end_time: time of collection last data point
        nxentry.create_dataset(
            "start_time", data=numpy.string_(self._params.input.start_time)
        )
        nxentry.create_dataset(
            "end_time", data=numpy.string_(self._params.input.end_time)
        )


"""
if __name__ == "__main__":
    import sys
    params = sys.argv[1:]
    with h5py.File(args.nxs_file, "x") as fh:
        NexusWriter(fh, params).write()
"""
