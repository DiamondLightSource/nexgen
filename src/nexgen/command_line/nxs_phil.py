"""
Define phil scopes that describe beamline, goniometer, detector and module.
"""

import freephil

# TODO FIXME .multiple for fast and slow axis doesn't seem to work correctly
module_scope = freephil.parse(
    """
    detector_module {
      num_modules = 1
        .type = int
        .help = "Number of modules - defaults to 1."
      module_offset = 0 *1 2
        .type = choice
        .help = "Decide whether to calculate offset of the module in regard to detector origin and creates corresponding field.
                Options:
                0 -> do not calculate module_offset
                1 -> un-normalized displacement, set module_offset to 1
                2 -> normalized displacement and set module_offset to magnitude of displacement"
      fast_axis = None
        .type = floats(size = 3)
        .help = "Fast axis at datum position"
      slow_axis = None
        .type = floats(size = 3)
        .help = "Slow axis at datum position"
      offsets = None
        .type = floats
        .help = "Axis offsets - one after the other - fast then slow"
      module_size = None
        .type = ints
        .help = "In case of multiple modules, pass the size of each single module"
    }
    """
)

detector_scope = freephil.parse(
    """
    detector {
      mode = *images events
        .type = choice
        .help = "Detector acquisition mode. Defaults to images. Only relevant for Tristan collections."
      description = None
        .type = str
        .help = "Detector class to record"
      detector_type = Pixel
        .type = str
        .help = "Detector type to record"
      sensor_material = *Si CdTe
        .type = choice
        .help = "Sensor material (e.g. silicon)"
      sensor_thickness = 0.0mm
        .type = str
        .help = "Sensor thickness, if unit is not specified defaults to mm"
      overload = None
        .type = int
        .help = "Pixels >= this value are invalid due to overloading"
      underload = -1
        .type = int
        .help = "Pixels <= this value are invalid"
      pixel_size = 0.0mm 0.0mm
        .type = strings
        .help = "Pixel size, if unit isn't passed defaults to mm (fast, slow)"
      beam_center = 0.0 0.0
        .type = floats(size = 2)
        .help = "Beam position on the detector (fast, slow)"
      flatfield = None
        .type = path
        .help = "If path is given, add flatfield correction data field"
      flatfield_applied = False
        .type = bool
        .help = "If the flatfield location is known, specify whether it's been applied of not."
      pixel_mask = None
        .type = path
        .help = "if path is given, add link to bad pixel mask"
      pixel_mask_applied = False
        .type = bool
        .help = "If the mask location is known, specify whether it's been applied of not."
      image_size = 0 0
        .type = ints(size = 2)
        .help = "Image size in pixels: (slow, fast)"
      exposure_time = None
        .type = str
        .help = "Nominal exposure time, eg 0.004s, if unit is not specified defaults to seconds"
      axes = None
        .type = strings
        .help = "Axis names for the detector axes. The detector sits on the last one."
      depends = None
        .type = strings
        .help = "Axis names for the axis dependencies"
      vectors = None
        .type = floats
        .help = "Axis vectors - one after the other"
      starts = None
        .type = floats
        .help = "Starting values for axes"
      ends = None
        .type = floats
        .help = "Ending values for axes, only different to start for scan axis"
      increments = None
        .type = floats
        .help = "Increment values for axes, non-zero only for scan axis"
      types = None
        .type = strings
        .help = "Axis types, rotation or translation"
      units = None
        .type = strings
        .help = "Axis units, from mm or deg"
      software_version = None
        .type = str
        .help = "Detector software version"
      bit_depth_readout = None
        .type = int
        .help = How many bits the electronics reads per pixel.
    }
    tristanSpec {
      detector_tick = 1562.5ps
        .type = str
        .help = "Tristan specific - detector tick, in ps"
      detector_frequency = 6.4e+08Hz
        .type = str
        .help = "Tristan specific - detector frequency, in Hz"
      timeslice_rollover = 18
        .type = int
        .help = "Tristan specific - timeslice rollover bits"
    }
    """
)

goniometer_scope = freephil.parse(
    """
    goniometer {
      axes = None
        .type = strings
        .help = "Axis names for the goniometer axes. Sample depends on the last one in the list"
      depends = None
        .type = strings
        .help = "Axis names for the axis dependencies"
      vectors = None
        .type = floats
        .help = "Axis vectors - one after the other"
      offsets = None
        .type = floats
        .help = "Axis offsets - one after the other"
      offset_units = None
        .type = strings
        .help = "Units of the axis offsets (usually mm)"
      starts = None
        .type = floats
        .help = "Starting values for axes"
      ends = None
        .type = floats
        .help = "Ending values for axes, only different to start for scan axis"
      increments = None
        .type = floats
        .help = "Increment values for axes, non-zero only for scan axis"
      types = None
        .type = strings
        .help = "Axis types, rotation or translation"
      units = None
        .type = strings
        .help = "Axis units, from mm or deg"
    }
    """
)

instrument_scope = freephil.parse(
    """
    source {
      name = Diamond Light Source
        .type = str
        .help = "Facility name"
      short_name = DLS
        .type = str
        .help = "Facility abbreviation"
      type = Synchrotron X-ray Source
        .type = str
        .help = "Facility type"
      beamline_name = None
        .type = str
        .help = "Beamline name"
      facility_id = None
        .type = str
        .help = "Identifier to use to define instrument name, when different from Diamond. Defaults to None"
      probe = None
        .type = str
        .help = "Type of radiation probe"
    }

    beam {
      wavelength = None
        .type = float
        .help = "Wavelength of incident beam, angstroms"
      flux = None
        .type = float
        .help = "Flux of incident beam, ph / s"
    }

    attenuator {
      transmission = None
        .type = float
        .help = "Attenuation of beam intensity"
    }
    pump_probe {
      pump_status = False
        .type = bool
        .help = "Pump probe experiment status."
      pump_exp = None
        .type = float
        .help = "Pump exposure time"
      pump_delay = None
        .type = float
        .help = "Pump delay"
    }
    """
)

timestamp_scope = freephil.parse(
    """
    start_time = None
      .type = str
      .help = "Experiment start time, pass either a timestamp or a string, eg '2021-09-20T10:20:30' or 'Tue Sep 28 2021 10:58:01'."
    end_time = None
      .type = str
      .help = "Experiment end time, pass either a timestamp or a string, eg '2021-09-20T10:20:30' or 'Tue Sep 28 2021 10:58:01'."
    time_zone = None
      .type = str
      .help = "Time zone offset from UTC."
    """
)

sample_scope = freephil.parse(
    """
    sample {
      name = None
        .type = str
        .help = "Descriptive name of the sample."
      temperature = None
        .type = str
        .help = "Sample temperature with units."
    }
    """
)

coord_system_scope = freephil.parse(
    """
    coord_system {
      convention = None
        .type = str
        .help = "Name of the new coordinate system."
      origin = None
        .type = floats
        .help = "Location of the origin e.g. 0,0,0."
      vectors = None
        .type = floats
        .help = "x,y,z axes vectors for the transformation."
    }
    """
)

if __name__ == "__main__":
    print(detector_scope.as_str())
    print(module_scope.as_str())
    print(goniometer_scope.as_str())
    print(instrument_scope.as_str())
    print(timestamp_scope.as_str())
    print(sample_scope.as_str())
