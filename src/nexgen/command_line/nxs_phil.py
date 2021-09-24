"""
Define phil scopes that describe beamline, goniometer, detector and module.
"""

import freephil

# Multiple modules should be considered
# Need to find a way to tell which module is which
# module_scope_string = """
# detector_module {
#   num_modules = 1
#     .type = int
#     .help = "Number of modules - defaults to 1." # not sure how useful right now...
#   module_offset = False
#     .type = bool
#     .help = "If set to true, calculates offset of the module in regard to detector origin and creates corresponding field"
#   fast_axis = 1 0 0
#     .multiple = True
#     .type = floats(size = 3)
#     .help = "Fast axis at datum position"
#   slow_axis = 0 -1 0
#     .multiple = True
#     .type = floats(size = 3)
#     .help = "Slow axis at datum position"
#   offsets = -0.1662 0.1721 0 0 0 0
#     .multiple = True
#     .type = floats
#     .help = "Axis offsets - one after the other - fast then slow"
#   module_size = 0 0
#     .multiple = True
#     .type = ints
#     .help = "In case of multiple modules, pass the size of aeach single module"
# }
# """
# module_scope = freephil.parse(module_scope_string)

module_scope = freephil.parse(
    """
    detector_module {
      num_modules = 1
        .type = int
        .help = "Number of modules - defaults to 1." # not sure how useful right now...
      module_offset = False
        .type = bool
        .help = "If set to true, calculates offset of the module in regard to detector origin and creates corresponding field"
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
      sensor_material = *Si CdTe
        .type = choice
        .help = "Sensor material (e.g. silicon)"
      sensor_thickness = 0.320
        .type = float
        .help = "Sensor thickness, mm"
      overload = 65535
        .type = int
        .help = "Pixels >= this value are invalid due to overloading"
      underload = -1
        .type = int
        .help = "Pixels <= this value are invalid"
      pixel_size = 0.075 0.075
        .type = floats(size = 2)
        .help = "Pixel size in mm"
      beam_center = 2214.355 2300.496
        .type = floats(size = 2)
        .help = "Beam position on the detector"
      flatfield = None
        .type = path
        .help = "If path is given, add flatfield correction data field"
      pixel_mask = None
        .type = path
        .help = "if path is given, add link to bad pixel mask"
      image_size = 4362 4148
        .type = ints(size = 2)
        .help = "Image size, slow, fast"
      exposure_time = 0.004
        .type = float
        .help = "Nominal exposure time, seconds"
      axes = two_theta det_z
        .type = strings
        .help = "Axis names for the detector axes"
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
      flux = 268717230611.358
        .type = float
        .help = "Flux of incident beam, ph / s"
    }

    attenuator {
      transmission = 1
        .type = float
        .help = "Attenuation of beam intensity"
    }
    """
)

if __name__ == "__main__":
    print(module_scope.as_str())
    print(detector_scope.as_str())
    print(goniometer_scope.as_str())
    print(beamline_scope.as_str())
