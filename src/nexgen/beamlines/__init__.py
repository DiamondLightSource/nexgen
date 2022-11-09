"""Utilities for writing NeXus files for beamlines at Diamond Light Source."""

import argparse

gonioAx_parser = argparse.ArgumentParser(add_help=False)
gonioAx_parser.add_argument("--axes", type=str, nargs="+", help="Axes names.")
gonioAx_parser.add_argument(
    "--ax-start", type=float, nargs="+", help="Axes start positions."
)
gonioAx_parser.add_argument(
    "--ax-inc", type=float, nargs="+", help="Eventual axes increments."
)
gonioAx_parser.add_argument(
    "--ax-end", type=float, nargs="+", help="Eventual axes ends."
)
gonioAx_parser.add_argument("--scan-axis", type=str, help="Identify scan axis.")

detAx_parser = argparse.ArgumentParser(add_help=False)
detAx_parser.add_argument(
    "--det-axes", type=str, nargs="+", help="Detector axes names."
)
detAx_parser.add_argument(
    "--det-start", type=float, nargs="+", help="Detector axes start positions."
)
