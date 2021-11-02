"""
Tools to get the information stored inside the _meta.h5 file and overwrite the phil scope.
"""
import h5py
import logging


overwrite_logger = logging.getLogger("NeXusGenerator.writer.overwrite")


def overwrite_beam(meta_file: h5py.File, name: str, beam):
    pass


def overwrite_detector(meta_file: h5py.File, detector):
    pass
