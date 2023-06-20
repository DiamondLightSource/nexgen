"""Diamond Light Source beamline utilities."""

from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class PumpProbe:
    """
    Define pump probe parameters.

    Args:
        status (bool): Pump on/off
        exposure (float, optional): Pump exposure time, in s.
        delay (float, optional): Pump delay, in s.
    """

    status: bool = False
    exposure: Optional[float] = None
    delay: Optional[float] = None
    pump_repeat: Optional[str] = "0"

    def __post_init__(self):
        if self.exposure:
            self.status = True


source = {
    "name": "Diamond Light Source",
    "short_name": "DLS",
    "type": "Synchrotron X-ray Source",
    "beamline_name": None,
}
