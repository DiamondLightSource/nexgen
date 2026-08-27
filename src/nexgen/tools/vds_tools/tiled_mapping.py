"""Create a Virtual DataSet with a strided mapping, ie mappaing every {n} frames from each file

For now only the JF1M functionality has been added, the full vds capabilities will be added later.
"""

import logging

import h5py
import numpy as np
from numpy.typing import DTypeLike

from nexgen.tools.constants import (
    jungfrau_fill_value,
    jungfrau_gap_size,
    jungfrau_mod_size,
)
from nexgen.tools.vds_tools.utils import find_datasets_in_file

tiled_vds_logger = logging.getLogger("nexgen.tools.vds_tools.utils")


def jungfrau_vds_writer(
    nxsfile: h5py.File,
    vds_shape: tuple | list,
    data_type: DTypeLike = np.uint16,
    source_dsets: list[str] | None = None,
):
    """Write VDS for Jungfrau 1M use case, with a tiled layout."""
    external_dsets = True
    entry_key = "data"
    frames = vds_shape[0]

    nxdata = nxsfile["/entry/data"]
    if not source_dsets:
        source_dsets = find_datasets_in_file(nxdata)
        external_dsets = False

    sources = []
    for dset in source_dsets:
        source_path = dset if external_dsets is True else "."
        source_name = entry_key if external_dsets is True else f"/entry/data/{dset}"
        source = h5py.VirtualSource(
            source_path, source_name, shape=(frames, *jungfrau_mod_size)
        )
        sources.append(source)

    layout = h5py.VirtualLayout(shape=vds_shape, dtype=data_type)
    # The first one is the upper one
    s0 = jungfrau_mod_size[0] + jungfrau_gap_size[0]
    layout[:, : jungfrau_mod_size[0], :] = sources[1][:, :, :]
    layout[:, s0:, :] = sources[0][:, :, :]

    nxdata.create_virtual_dataset(entry_key, layout, fillvalue=jungfrau_fill_value)
