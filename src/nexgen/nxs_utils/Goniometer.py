"""
Object definition for goniometer
"""

from typing import List

from .Axes import Axis


class Goniometer:
    def __init__(
        self,
        axes: List[Axis],
        # scan_axes, #List[ScanAxis] = None,
        scan: dict = None,
    ):
        self.axes_list = axes
        # self.scan_axes = scan_axes
        self.scan = scan

    def __repr__(self) -> str:
        msg = ""
        for ax in self.axes_list:
            msg += f"{ax.name}: {ax.start_pos} => {ax.transformation_type} on {ax.depends} \n\t"
        return f"Goniometer axes: \n\t {msg}"

    def _define_scan(self):
        # Also if only scan is passed, grab number of images from it
        # if rotation or translation can be determined from axes names in scan dict
        if self.scan and self.scan_axes:
            print("Here just check that they are the same")
            return self.scan
        if self.scan_axes:
            print("Here calculate the scan points")
            return
        if self.scan:
            print("Here generate the end position for the scan axes")
            return

    def _generate_goniometer_dict(self):
        # Also build end positions here
        goniometer = {
            "axes": [ax.name for ax in self.axes_list],
            "depends": [ax.depends for ax in self.axes_list],
            "types": [ax.transformation_type for ax in self.axes_list],
            "units": [ax.units for ax in self.axes_list],
            "starts": [ax.start_pos for ax in self.axes_list],
            "increments": [ax.increment for ax in self.axes_list],
        }
        return goniometer

    # calculate scans maybe here, with rotation axis thing
