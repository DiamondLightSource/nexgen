"""
Tools to extract goniometer and detector parameters from GDA JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path

from nexgen.nxs_utils import Axis, EigerDetector, TransformationType, TristanDetector
from nexgen.nxs_utils.detector import DetectorType, UnknownDetectorTypeError
from nexgen.utils import Point3D


class JSONParamsIO:
    """Read JSON file and exctract parameters."""

    def __init__(self, json_file: Path | str):
        self.json_file = json_file
        self.params = self._read_file()

    def _read_file(self) -> dict:
        with open(self.json_file, "r") as fh:
            params = json.load(fh)
        return params

    def _find_axis_depends_on(self, dep_val: str) -> str:
        depends = dep_val.split("_")[1] if "_" in dep_val else dep_val
        if depends in ["x", "y", "z"]:
            depends = f"sam_{depends}"
        return depends

    def get_coordinate_frame(self) -> str:
        """Get the coordinate frame from geometry json file."""
        return self.params["geometry"]

    def get_goniometer_axes_from_file(self) -> list[Axis]:
        """Read the axes information from the GDA-supplied json file."""
        axes_list = []
        for v in self.params.values():
            if isinstance(v, dict) and v["location"] == "sample":
                ax_depends = self._find_axis_depends_on(v["depends_on"])
                ax_type = (
                    TransformationType.ROTATION
                    if v["type"] == "rotation"
                    else TransformationType.TRANSLATION
                )
                axes_list.append(
                    Axis(v["ds_name"], ax_depends, ax_type, tuple(v["vector"]))
                )
        return axes_list

    def get_detector_axes_from_file(self) -> list[Axis]:
        """Read the detector axes information from the GDA-supplied json file."""
        axes_list = []
        for v in self.params.values():
            if isinstance(v, dict) and v["location"] == "detector":
                ax_type = (
                    TransformationType.ROTATION
                    if v["type"] == "rotation"
                    else TransformationType.TRANSLATION
                )
                axes_list.append(
                    Axis(v["ds_name"], v["depends_on"], ax_type, tuple(v["vector"]))
                )
        return axes_list

    def get_detector_params_from_file(self) -> DetectorType:
        """Read the detector parameters from the GDA-supplied json file."""
        if "tristan" in self.params.keys():
            tristan_params = self.params["tristan"]
            material = (
                "Si"
                if tristan_params["sensor_material"] == "Silicon"
                else tristan_params["sensor_material"]
            )
            thickness = (
                str(tristan_params["sensor_thickness"])
                + tristan_params["sensor_thickness_units"]
            )
            pix = [
                str(i) + tristan_params["pixel_size_units"]
                for i in tristan_params["pixel_size_sf"][::-1]
            ]
            det_params = TristanDetector(
                description=tristan_params["description"],
                image_size=tristan_params["data_size_sf"][::-1],
                sensor_material=material,
                sensor_thickness=thickness,
                pixel_size=pix,
                detector_type=tristan_params["detector_type"],
            )
        elif "eiger" in self.params.keys():
            eiger_params = self.params["eiger"]
            material = eiger_params["sensor_material"]
            pix = [
                str(i) + eiger_params["pixel_size_units"]
                for i in eiger_params["pixel_size"]
            ]
            if material == "Silicon":
                material = "Si"
            det_params = EigerDetector(
                description=eiger_params["description"],
                image_size=eiger_params["size"],
                sensor_material=material,
                overload=50649,
                underload=-1,
                pixel_size=pix,
            )
        else:
            raise UnknownDetectorTypeError("Unknown detector in GDA JSON file.")

        return det_params

    def get_fast_and_slow_direction_vectors_from_file(
        self,
        det_type: str,
    ) -> tuple[Point3D, Point3D]:
        """Read detector fast and slow axes from the GDA-supplied json file."""
        det_name = "eiger" if "eiger" in det_type.lower() else "tristan"
        det_params = self.params[det_name]
        fast_axis = Point3D(
            x=det_params["fast_dir"][0],
            y=det_params["fast_dir"][1],
            z=det_params["fast_dir"][2],
        )
        slow_axis = Point3D(
            x=det_params["slow_dir"][0],
            y=det_params["slow_dir"][1],
            z=det_params["slow_dir"][2],
        )
        return fast_axis, slow_axis
