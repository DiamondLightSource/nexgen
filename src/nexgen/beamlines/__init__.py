"""Diamond Light Source beamline utilities."""

from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json


@dataclass
@dataclass_json
class PumpProbe:
    """Pump probe parameters."""

    status: bool = False
    exposure: Optional[float] = None
    delay: Optional[float] = None


source = {
    "name": "Diamond Light Source",
    "short_name": "DLS",
    "type": "Synchrotron X-ray Source",
    "beamline_name": None,
}

eiger_meta_links = [
    [
        "pixel_mask",
        "pixel_mask_applied",
        "flatfield",
        "flatfield_applied",
        "threshold_energy",
        "bit_depth_readout",
        "detector_readout_time",
        "serial_number",
    ],
    ["software_version"],
]
