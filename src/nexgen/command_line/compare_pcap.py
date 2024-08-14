import math
import sys
from argparse import ArgumentParser, BooleanOptionalAction
from collections.abc import Sequence
from enum import Enum
from math import dist
from typing import NamedTuple

import h5py

MAX_DIST_MM = 1e-3

PCAP_DATASETS = ["INENC1.VAL.Mean", "INENC2.VAL.Mean", "INENC3.VAL.Mean"]


class GridPlane(Enum):
    PLANE_XY = 0
    PLANE_XZ = 1


def main() -> int:
    """A tool to compare gridscan pcap position output with the positions reported in the gridscan .h5 grid
    files"""
    parser = ArgumentParser(
        prog="compare-pcap",
        description="A tool to compare gridscan pcap position output with the positions reported "
        "in the gridscan .h5 grid",
    )
    parser.add_argument("--csv", action=BooleanOptionalAction, help="Output as CSV")
    parser.add_argument(
        "--verbose", action=BooleanOptionalAction, help="Output more info"
    )
    parser.add_argument("xy_nexus_file", help="xy gridscan nexus file")
    parser.add_argument("xz_nexus_file", help="xz gridscan nexus file")
    parser.add_argument("pcap_file", help="Path to the PCAP data file")
    args = parser.parse_args()

    reported_positions = _load_nexus_data_xy_xz(args.xy_nexus_file, args.xz_nexus_file)
    pcap_positions = _load_pcap_data(args.pcap_file, PCAP_DATASETS)

    if args.csv:
        _output_to_csv(reported_positions, pcap_positions)
    else:
        compare_reported_and_pcap_positions(
            reported_positions, pcap_positions, args.verbose
        )

    return 0


class XYZTuple(NamedTuple):
    frame_index: int
    plane: GridPlane | None
    sam_x: float
    sam_y: float
    sam_z: float

    @property
    def sam_pos(self) -> Sequence[float]:
        return [self.sam_x, self.sam_y, self.sam_z]

    def __str__(self):
        return f"idx={self.frame_index}, ({self.sam_x:.4f}, {self.sam_y:.4f}, {self.sam_z:.4f}"


def compare_reported_and_pcap_positions(
    reported_positions: list[XYZTuple], pcap_positions: list[XYZTuple], verbose: bool
):
    assert len(reported_positions) == len(pcap_positions)

    print("XY plane comparison")
    nexus_xy = [p for p in reported_positions if p.plane == GridPlane.PLANE_XY]
    pcap_xy = pcap_positions[: len(nexus_xy)]
    _compare_reported_and_pcap_for_plane(nexus_xy, pcap_xy, verbose)

    print("XZ plane comparison")
    nexus_xz = [p for p in reported_positions if p.plane == GridPlane.PLANE_XZ]
    pcap_xz = pcap_positions[len(pcap_xy) :]
    _compare_reported_and_pcap_for_plane(nexus_xz, pcap_xz, verbose)


def _compare_reported_and_pcap_for_plane(
    reported_positions: list[XYZTuple], pcap_positions: list[XYZTuple], verbose: bool
):
    for reported_pos, pcap_pos in zip(reported_positions, pcap_positions):
        distance = dist(reported_pos.sam_pos, pcap_pos.sam_pos)

        if verbose:
            print(f"{reported_pos} <=> {pcap_pos}, distance = {distance:.4f}")

    m, v = _generate_stats_for_axis(
        reported_positions, pcap_positions, lambda pos: pos.sam_x
    )
    print(f"X axis: mean difference={m}, sd={math.sqrt(v):.6f}")
    m, v = _generate_stats_for_axis(
        reported_positions, pcap_positions, lambda pos: pos.sam_y
    )
    print(f"Y axis: mean difference={m}, sd={math.sqrt(v):.6f}")
    m, v = _generate_stats_for_axis(
        reported_positions, pcap_positions, lambda pos: pos.sam_z
    )
    print(f"Z axis: mean difference={m}, sd={math.sqrt(v):.6f}")


def _output_to_csv(reported_positions: list[XYZTuple], pcap_positions: list[XYZTuple]):
    assert len(reported_positions) == len(pcap_positions)

    print("nexus x, nexus y, nexus z, pcap x, pcap y, pcap z, dx, dy, dz, dist")
    for reported_pos, pcap_pos in zip(reported_positions, pcap_positions):
        distance = dist(reported_pos.sam_pos, pcap_pos.sam_pos)
        print(
            f"{reported_pos.sam_x}, {reported_pos.sam_y}, {reported_pos.sam_z}, {pcap_pos.sam_x}, {pcap_pos.sam_y}, {pcap_pos.sam_z}, "
            f"{reported_pos.sam_x - pcap_pos.sam_x}, {reported_pos.sam_y - pcap_pos.sam_y}, "
            f"{reported_pos.sam_z - pcap_pos.sam_z}, {distance}"
        )


def _generate_stats_for_axis(
    required_positions: list[XYZTuple], pcap_positions: list[XYZTuple], accessor
):
    filtered_expected = [
        accessor(ep)
        for ep, ap in zip(required_positions, pcap_positions)
        if not math.isnan(accessor(ap))
    ]
    filtered_actual = [
        accessor(ap) for ap in pcap_positions if not math.isnan(accessor(ap))
    ]

    distances = [ap - ep for ap, ep in zip(filtered_actual, filtered_expected)]
    sum_distances = sum(distances)
    # We expect 0.5 boxsize average difference
    mean_distance = sum_distances / len(filtered_actual)
    variance = sum((d - mean_distance) * (d - mean_distance) for d in distances) / len(
        filtered_actual
    )

    return mean_distance, variance


def _load_nexus_data_xy_xz(xy_nexus_file: str, xz_nexus_file: str) -> list[XYZTuple]:
    xyz_data = _load_nexus_data(xy_nexus_file, GridPlane.PLANE_XY)
    xyz_data.extend(_load_nexus_data(xz_nexus_file, GridPlane.PLANE_XZ))
    return xyz_data


def _load_nexus_data(nexus_file: str, plane: GridPlane) -> list[XYZTuple]:
    """Load from the nexus files, the motor xyz positions for each frame"""
    with h5py.File(nexus_file, "r") as h5_file:
        num_frames = h5_file["/entry/data/data"].shape[0]
        xyz_data = []

        sam_x_dataset = h5_file["/entry/data/sam_x"]
        sam_y_dataset = h5_file["/entry/data/sam_y"]
        sam_z_dataset = h5_file["/entry/data/sam_z"]

        for i in range(0, num_frames):
            xyz_data.append(
                XYZTuple(i, plane, sam_x_dataset[i], sam_y_dataset[i], sam_z_dataset[i])
            )

    return xyz_data


def _load_pcap_data(path_to_pcap_file: str, axis_names: list[str]) -> list[XYZTuple]:
    """Load the pcap data for each frame from the pcap file"""
    with h5py.File(path_to_pcap_file, "r") as h5_file:
        x_data = _extract_pcap_axis_data(h5_file, axis_names[0])
        y_data = _extract_pcap_axis_data(h5_file, axis_names[1])
        z_data = _extract_pcap_axis_data(h5_file, axis_names[2])
        assert len(x_data) == len(y_data) == len(z_data)

        return [
            XYZTuple(i, None, x, y, z)
            for i, (x, y, z) in enumerate(zip(x_data, y_data, z_data))
        ]


def _extract_pcap_axis_data(h5_file: h5py.File, axis_name: str) -> Sequence[float]:
    return h5_file[axis_name]


if __name__ == "__main__":
    sys.exit(main())
