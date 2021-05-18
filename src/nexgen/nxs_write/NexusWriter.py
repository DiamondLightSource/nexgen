"""
Writer for NeXus format files.
"""

import h5py

# import numpy as np

# from . import calculate_origin
# from .. import imgcif2mcstas, create_attributes, set_dependency
# from ..data import generate_image_data, generate_event_data

# Base classes I need functions for
# NXdata
def write_NXdata(nxsfile: h5py.File, goniometer, datafile, scan_axis=None):
    """
    Args:
        nxsfile:
        goniometer:
    """
    # 1 - check whether file already has nxentry, if it doesn't create it
    # 2 - determine whether to generate images or events (input argument)
    # 3 - number of images/ number of events
    # actually 2 and 3 are probably better handled somewhere else
    # ad here only write the link to the data file(s)
    # 4 - from goniometer determine scan axis and range
    # 5 - write nxdata with attributes
    # 6 - write scan axis dataset
    pass


# NXinstrument
def write_NXinstrument(nxsfile: h5py.File, source, beam, attenuator, detector):
    # 1 - check whether file already has nxentry, if it doesn't create it
    # 2 - write nxinstrument and attributes
    # 3 - write nxattenuator
    # 4 - write nxbeam
    # 5 - write nxsource
    # 6 - call write_NXdetector
    # 7 - call write_NXpositioner
    pass


# NXdetector
def write_NXdetector(nxsfile: h5py.File, detector):
    # 1 - checke whether nxinstrument exists, if not create it
    # 2 - create nxdetector group with attribute
    # 3 - write all datasets
    # 4- check for mask and flatfield files
    # 5 - if images write overload and underload
    # 6 - call write_NXmodule
    # 7 - call write_NXcollection
    pass


# NXmodule
def write_NXmodule(nxdetector, module):
    # 1- create nxdetectormodule group
    # 2 - check how many modules
    # 3 - write relevant datasets
    # 4 - if module_offset is True, calculate and write it
    # 4 - and correct dependency tree accordingly
    pass


# NXsample
def write_NXsample(nxsfile: h5py.File, goniometer):
    # 1 - check whether file already has nxentry, if it doesn't create it
    # 2 - create nxsample with attributes
    # 3 - look for nxbeam in file, if there make link
    # 4 - write sample_depends_on
    # 5 - create nxtransformation
    # 6 - determine scan axis
    # 7 - try: make a link to scan axis in nxdata
    # 7 - if it doesn't exist, write here
    # 8 - write sample_ groups from goniometer (only angles)
    # 9 - write links to sample_ in transformations
    pass


# Plus:
# NXCollection (detectorSpecific)
def write_NXcollection(nxdetector, detector, n_images=None):
    # 1 - create detectorSpecific group
    # 2 - write x_pixels and y_pixels
    # 3 - if images write n_images
    # 4 - if events write tick time and frequency
    pass


# NXpositioner (det_z and 2theta)
def write_NXpositioner(nxinstrument, detector):
    # 1 - write detector_z
    # 2 - write entry/instrument/transformation with link to det_z
    # 3 - add 2 theta arm if there and add link in transformations
    pass


# General writing
def write_full_nexus_file():
    # 1 - write data file(s)
    # 2 - write nexus components one by one
    pass
