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
      fast_axis = 1 0 0
        .type = floats(size = 3)
        .help = "Fast axis at datum position"
      slow_axis = 0 -1 0
        .type = floats(size = 3)
        .help = "Slow axis at datum position"
      offsets = -0.1662 0.1721 0 0 0 0
        .multiple = True
        .type = floats
        .help = "Axis offsets - one after the other - fast then slow"
      module_size = 0 0
        .multiple = True
        .type = ints
        .help = "In case of multiple modules, pass the size of aeach single module"
    }
    """
)

detector_scope = freephil.parse(
    """
    detector {
      description = Eiger 2XE 16M
        .type = str
        .help = "Detector class to record"
      detector_type = Pixel
        .type = str
        .help = "Detector type to record"
      sensor_material = *Si CdTe
        .type = choice
        .help = "Sensor material (e.g. silicon)"
      sensor_thickness = 0.320mm
        .type = str
        .help = "Sensor thickness, if unit is not specified defaults to mm"
      overload = 65535
        .type = int
        .help = "Pixels >= this value are invalid due to overloading"
      underload = -1
        .type = int
        .help = "Pixels <= this value are invalid"
      pixel_size = 0.075mm 0.075mm
        .type = strings
        .help = "Pixel size, if unit isn't passed defaults to mm"
      beam_center = 2214.355 2300.496
        .type = floats(size = 2)
        .help = "Beam position on the detector"
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
      image_size = 4148 4362
        .type = ints(size = 2)
        .help = "Image size in pixels: (fast, slow)"
      exposure_time = 0.004s
        .type = str
        .help = "Nominal exposure time, if unit is not specified defaults to seconds"
      axes = two_theta det_z
        .type = strings
        .help = "Axis names for the detector axes. The detector sits on the last one."
      depends = . two_theta
        .type = strings
        .help = "Axis names for the axis dependencies"
      vectors = 1 0 0 0 0 -1
        .type = floats
        .help = "Axis vectors - one after the other"
      starts = 0.0 100.0
        .type = floats
        .help = "Starting values for axes"
      ends = 0.0 100.0
        .type = floats
        .help = "Ending values for axes, only different to start for scan axis"
      increments = 0.0 0.0
        .type = floats
        .help = "Increment values for axes, non-zero only for scan axis"
      types = rotation translation
        .type = strings
        .help = "Axis types, rotation or translation"
      units = deg mm
        .type = strings
        .help = "Axis units, from mm or deg"
      software_version = None
        .type = str
        .help = "Detector software version"
    }
    tristanSpec {
      detector_tick = None          # 1562.5ps
        .type = str
        .help = "Tristan specific - detector tick, in ps"
      detector_frequency = None     # 6.4e+08Hz
        .type = str
        .help = "Tristan specific - detector frequency, in Hz"
      timeslice_rollover = None     # 18
        .type = int
        .help = "Tristan specific - timeslice rollover bits"
    }
    """
)

goniometer_scope = freephil.parse(
    """
    goniometer {
      axes = omega sam_z sam_y sam_x chi phi
        .type = strings
        .help = "Axis names for the goniometer axes. Sample depends on the last one in the list"
      depends = . omega sam_z sam_y sam_x chi
        .type = strings
        .help = "Axis names for the axis dependencies"
      vectors = 1 0 0 0 0 1 0 1 0 1 0 0 0 0 1 1 0 0
        .type = floats
        .help = "Axis vectors - one after the other"
      offsets = 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
        .type = floats
        .help = "Axis offsets - one after the other"
      offset_units = mm mm mm mm mm mm
        .type = strings
        .help = "Units of the axis offsets"
      starts = 0.0 0.0 0.0 0.0 0.0 0.0
        .type = floats
        .help = "Starting values for axes"
      ends = 90.0 0.0 0.0 0.0 0.0 0.0
        .type = floats
        .help = "Ending values for axes, only different to start for scan axis"
      increments = 0.1 0.0 0.0 0.0 0.0 0.0
        .type = floats
        .help = "Increment values for axes, non-zero only for scan axis"
      types = rotation translation translation translation rotation rotation
        .type = strings
        .help = "Axis types, rotation or translation"
      units = deg mm mm mm deg deg deg
        .type = strings
        .help = "Axis units, from mm or deg"
    }
    """
)

beamline_scope = freephil.parse(
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
      beamline_name = I19-2
        .type = str
        .help = "Beamline name"
    }

    beam {
      wavelength = 0.979590
        .type = float
        .help = "Wavelength of incident beam, angstroms"
      flux = None
        .type = float
        .help = "Flux of incident beam, ph / s"
    }

    attenuator {
      transmission = 1
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
    """
)

if __name__ == "__main__":
    print(detector_scope.as_str())
    print(module_scope.as_str())
    print(goniometer_scope.as_str())
    print(beamline_scope.as_str())
    print(timestamp_scope.as_str())
