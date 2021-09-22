"""General utilities for comamnd line tools"""

import argparse

from .. import __version__

version_parser = argparse.ArgumentParser(add_help=False)
version_parser.add_argument(
    "-V",
    "--version",
    action="version",
    version="%(prog)s: NeXus generation tools {version}".format(version=__version__),
)


class _CheckFileExtension(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        pass
