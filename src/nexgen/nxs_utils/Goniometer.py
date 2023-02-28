"""
Object definition for goniometer
"""

from typing import List

from . import GridScanOptions
from .Axes import Axis
from .ScanUtils import identify_grid_scan_axes, identify_osc_axis


class Goniometer:
    def __init__(
        self,
        axes: List[Axis],
        scan: dict = None,
        grid_scan_options: GridScanOptions | None = None,
    ):
        self.axes_list = axes
        self.osc_scan, self.grid_scan = self.define_scan(scan, grid_scan_options)

    def __repr__(self) -> str:
        msg = ""
        for ax in self.axes_list:
            msg += f"{ax.name}: {ax.start_pos} => {ax.transformation_type} on {ax.depends} \n\t"
        return f"Goniometer axes: \n\t {msg}"

    def define_scan(self, scan, grid_scan_options):
        osc_scan = {}
        grid_scan = {}
        if scan:
            # Look at keys to see if rotation or grid scan
            scan_axes = list(scan.keys())
            for _ in scan_axes:
                pass
        else:
            osc_axis = identify_osc_axis(self.axes_list)
            osc_idx = [n for n, ax in enumerate(self.axes_list) if ax.name == osc_axis][
                0
            ]
            if not grid_scan_options:
                transl_axes = identify_grid_scan_axes(self.axes_list)
                transl_idx = [
                    n for n, ax in enumerate(self.axes_list) if ax.name in transl_axes
                ]
                # get axes in correct order
            else:
                transl_axes = grid_scan_options.axes_order
            snaked = True if not grid_scan_options else grid_scan_options.snaked
            print(snaked, osc_idx, transl_idx)
            # Look at which axes move, check for options
            # if options not there, assume snaked and order from gonio
        return osc_scan, grid_scan

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
