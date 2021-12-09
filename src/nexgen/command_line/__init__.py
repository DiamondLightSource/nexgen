"""General utilities for comamnd line tools"""

import argparse

from pathlib import Path

from .. import __version__

version_parser = argparse.ArgumentParser(add_help=False)
version_parser.add_argument(
    "-V",
    "--version",
    action="version",
    version="%(prog)s: NeXus generation tools {version}".format(version=__version__),
)

detectormode_parser = argparse.ArgumentParser(add_help=False)
group = detectormode_parser.add_mutually_exclusive_group()
group.add_argument(
    "-i",
    "--num-images",
    help="Number of blank images to be written per file. Overrides increment.",
    type=int,
)
group.add_argument(
    "-e",
    "--num-events",
    help="Size of event stream to be written per file.",
    type=int,
)


class _CheckFileExtension(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        condition = any("filename" in v for v in values)
        if condition is True:
            i = ["filename" in v for v in values].index(True)
            fname = Path(values[i]).expanduser().resolve()
            ext = fname.suffix
            if ext != ".h5" and ext != ".nxs":
                print(
                    f"You specified an invalid extension {ext} for the output file.\n"
                    f"It will be saved to {fname.stem}.nxs instead."
                )
                values[i] = f"{fname.stem}.nxs"
        setattr(namespace, self.dest, values)


# Define subparsers for NeXus generator
nexus_parser = argparse.ArgumentParser(add_help=False)
nexus_parser.add_argument("phil_args", nargs="*")

demo_parser = argparse.ArgumentParser(add_help=False)
demo_parser.add_argument("phil_args", nargs="*", action=_CheckFileExtension)

# Define subparsesrs for NeXus copy
full_copy_parser = argparse.ArgumentParser(add_help=False)
full_copy_parser.add_argument("phil_args", nargs="*")

tristan_copy_parser = argparse.ArgumentParser(add_help=False)
tristan_copy_parser.add_argument("phil_args", nargs="*")
tristan_group = tristan_copy_parser.add_mutually_exclusive_group(required=True)
tristan_group.add_argument(
    "-o",
    "--osc-angle",
    help="Oscillation angle, in degrees",
    type=float,
)
tristan_group.add_argument(
    "-n",
    "--num-bins",
    help="Number of binnes images",
    type=int,
)


def add_tristan_spec(detector, tristanSpec):
    """
    Add metadata specific to LATRD Tristan to detector scope.

    Args:
        detector (scope_extract):      Scope defining the detector
        tristanSpec (scope_extract):   Scope defining Tristan specific input
    """
    for k, v in tristanSpec.__dict__.items():
        if "__phil" in k:
            continue
        detector.__inject__(k, v)
