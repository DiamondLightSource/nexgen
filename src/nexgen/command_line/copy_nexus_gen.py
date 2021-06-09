"""
Command line tool to copy metadata from existing NeXus files.
"""

import os
import sys

import freephil

from ..nxs_copy import CopyNexus

copy_scope = freephil.parse(
    """
    input {
      data_file_name = None
        .type = path
        .help = "HDF5 data file."
      original_nexus_file = None
        .type = path
        .help = "NeXus file with experiment metadata to be copied."
      mode = *images pseudo-events
        .type = choice
        .help = "Type od data in HDF5 file."
      simple_copy = False
        .type = bool
        .help = "If True, the full NeXus tree is copied, including NXdata."
    }
    """
)


def main():
    args = sys.argv[1:]
    clai = copy_scope.command_line_argument_interpreter()
    working = copy_scope.fetch(clai.process_and_fetch(args))
    params = working.extract()

    print("Copy metadata from one NeXus file to another.")
    data_file = os.path.basename(params.input.data_file_name)
    nexus_file = os.path.basename(params.input.original_nexus_file)
    print(f"Image data file name: {data_file}")
    print(f"Original Tristan NeXus file: {nexus_file}")

    print(f"Data mode: {params.input.mode}")
    if params.input.mode == "images":
        if params.input.simple_copy is True:
            CopyNexus.images_nexus(
                params.input.data_file_name,
                params.input.original_nexus_file,
                simple_copy=params.input.simple_copy,
            )
        else:
            CopyNexus.images_nexus(
                params.input.data_file_name, params.input.original_nexus_file
            )
    elif params.input.mode == "pseudo-events":
        CopyNexus.pseudo_events_nexus(
            params.input.data_file_name, params.input.original_nexus_file
        )
    else:
        sys.exit(f"Please pass a valid data mode.")
    print("All done!")


if __name__ == "__main__":
    main()
