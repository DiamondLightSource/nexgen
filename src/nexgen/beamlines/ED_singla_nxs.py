"""
Create a nexus file for electron diffraction collections using singla detector.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..nxs_write.NXmxWriter import EDNXmxFileWriter

# Define entry_key if dealing with singla detector
SINGLA_DATA_ENTRY_KEY = "/entry/data/data"


def singla_nexus_writer(
    master_file: Path | str,
    datafiles: List[Path | str],
    outdir: Path | str = None,
):
    try:
        EDFileWriter = EDNXmxFileWriter()
        print(EDFileWriter)
    except Exception as err:
        print(err)
