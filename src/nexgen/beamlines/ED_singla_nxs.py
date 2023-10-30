"""
Create a nexus file for electron diffraction collections using singla detector.
"""

from __future__ import annotations

from ..nxs_write.NXmxWriter import EDNXmxFileWriter


def singla_nexus_writer():
    try:
        EDFileWriter = EDNXmxFileWriter()
        print(EDFileWriter)
    except Exception as err:
        print(err)
