"""
Object definition for goniometer
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from numpy.typing import ArrayLike

from . import GridScanOptions
from .Axes import Axis
from .ScanUtils import calculate_scan_points, identify_grid_scan_axes, identify_osc_axis


class Goniometer:
    def __init__(
        self,
        axes: List[Axis],
        scan: Dict[str, ArrayLike] | None = None,
    ):
        self.axes_list = axes
        self.scan = scan

    def __repr__(self) -> str:
        msg = ""
        for ax in self.axes_list:
            msg += f"{ax.name}: {ax.start_pos} => {ax.transformation_type} on {ax.depends} \n\t"
        return f"Goniometer axes: \n\t{msg}"

    def _find_axis_in_goniometer(self, val: str) -> int:
        """Find the index of the axis matching the input string."""
        idx = [n for n, ax in enumerate(self.axes_list) if ax.name == val]
        if len(idx) == 0:
            return None
        return idx[0]

    def define_scan_from_goniometer_axes(
        self,
        grid_scan_options: GridScanOptions | None = None,
        rev_rotation: bool = False,
    ) -> Tuple[Dict, Dict]:
        """Define oscillation and grid scan ranges."""
        # Not to be used for EVENTS! In that case just omega/phi (start, end)
        if self.scan:
            # Look at keys to see if rotation or grid scan
            scan_axes = list(self.scan.keys())
            # Actually I just need one
            ax_idx = self._find_axis_in_goniometer(scan_axes[0])
            if self.axes_list[ax_idx].transformation_type == "rotation":
                osc_scan = self.scan
                transl_scan = None
            else:
                # Find number of scan points
                tot_num_imgs = len(self.scan[scan_axes[0]])
                osc_axis = identify_osc_axis(self.axes_list)
                osc_idx = self._find_axis_in_goniometer(osc_axis)
                osc_scan = calculate_scan_points(
                    self.axes_list[osc_idx], rotation=True, tot_num_imgs=tot_num_imgs
                )
                transl_scan = self.scan

            return osc_scan, transl_scan

        osc_axis = identify_osc_axis(self.axes_list)
        osc_idx = [n for n, ax in enumerate(self.axes_list) if ax.name == osc_axis][0]

        transl_axes = (
            grid_scan_options.axes_order
            if grid_scan_options
            else identify_grid_scan_axes(self.axes_list)
        )

        if len(transl_axes) == 0:
            if rev_rotation is True:
                self.axes_list[osc_idx].increment = -self.axes_list[osc_idx].increment
            osc_scan = calculate_scan_points(self.axes_list[osc_idx], rotation=True)
            return osc_scan, None

        transl_idx = [self._find_axis_in_goniometer(ax) for ax in transl_axes]
        if len(transl_axes) == 1:
            transl_scan = calculate_scan_points(self.axes_list[transl_idx[0]])
        else:
            snaked = True if not grid_scan_options else grid_scan_options.snaked
            transl_scan = calculate_scan_points(
                self.axes_list[transl_idx[0]],
                self.axes_list[transl_idx[1]],
                snaked=snaked,
            )

        tot_num_imgs = len(list(transl_scan.values())[0])
        osc_scan = calculate_scan_points(
            self.axes_list[0], rotation=True, tot_num_imgs=tot_num_imgs
        )

        return osc_scan, transl_scan

    def define_scan_axes_for_event_mode(self) -> Tuple[Dict, Dict]:
        """Define oscillation and grid scan ranges for event-mode datasets."""
        if self.scan:
            scan_axis = list(self.scan.keys())
            ax_idx = self._find_axis_in_goniometer(scan_axis[0])
            if self.axes_list[ax_idx].transformation_type == "rotation":
                return self.scan, None
            else:
                # We actually always pass a rotation here but future proofing
                return {"omega": (0.0, 0.0)}, self.scan
        else:
            osc_axis = identify_osc_axis(self.axes_list)
            osc_idx = self.axes_list.index(osc_axis)
            osc_scan = {
                osc_axis: (
                    self.axes_list[osc_idx].start_pos,
                    self.axes_list[osc_idx].end_pos,
                )
            }
            # Now this is a bit more complicated because for tristan we already give it (start, stop)
            # But there will be no increment
            # To figure out how this actually will work, I need to fix the Tristan writer
            return osc_scan, None

    def _generate_goniometer_dict(self):
        goniometer = {
            "axes": [ax.name for ax in self.axes_list],
            "depends": [ax.depends for ax in self.axes_list],
            "types": [ax.transformation_type for ax in self.axes_list],
            "units": [ax.units for ax in self.axes_list],
            "starts": [ax.start_pos for ax in self.axes_list],
            "increments": [abs(ax.increment) for ax in self.axes_list],
            "ends": [ax.end_pos for ax in self.axes_list],
        }
        return goniometer
