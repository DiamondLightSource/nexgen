"""General utilities for parsing in comamnd line tools"""

import argparse
from pathlib import Path

from .. import __version__
from ..utils import P


# Define a parser for the basic collection parameters
class ImportCollectAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        input_file, visitpath, filename_root = self.find_import_args(values)
        setattr(namespace, self.dest, input_file)
        setattr(namespace, "visitpath", visitpath)
        setattr(namespace, "filename_root", filename_root)

    @staticmethod
    def find_import_args(val) -> tuple[str]:
        input_file = Path(val).expanduser().resolve()
        visitpath = input_file.parent
        filename_root = P.fullmatch(input_file.stem)[1]
        return input_file, visitpath, filename_root


class CheckFileExtensionAction(argparse.Action):
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


version_parser = argparse.ArgumentParser(add_help=False)
version_parser.add_argument(
    "-V",
    "--version",
    action="version",
    version=f"%(prog)s: NeXus generation tools {__version__}",
)

config_parser = argparse.ArgumentParser(add_help=False)
config_parser.add_argument(
    "--config",
    type=str,
    required=True,
    help="A YAML or JSON file with the configuration paramters.",
)

vds_parser = argparse.ArgumentParser(add_help=False)
# vds_parser.add_argument(
#     "--vds-type",
#     type=str,
#     choices=["dataset", "file"],
#     default="dataset",
#     help="Choose whether to write the vds as a detaset or a file. Defaults to dataset."
# )
vds_parser.add_argument(
    "--vds-offset", type=int, default=0, help="Start image for the vds."
)
vds_parser.add_argument(
    "--no-vds", action="store_false", help="Do not write a vds file."
)
