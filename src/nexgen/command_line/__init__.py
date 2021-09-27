"""General utilities for comamnd line tools"""

import argparse

from pathlib import Path

from nexgen import __version__

# from .. import __version__

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


# class
