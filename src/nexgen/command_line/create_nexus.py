"""
Command line tool to generate a NeXus file.
"""

# import sys

# sys.path.append("/home/uhz96441/local/Python3_dials/modules/nexgen/src/nexgen/")

import os

# import h5py
import logging
import argparse

import freephil

# import nexgen.phil

# import writer

logger = logging.getLogger("NeXusWriter")

master_phil = freephil.parse(
    """
    output {
      master_file_name = nexus_master.h5
        .type = path
        .help = "Filename for master file"
    }

    input {
      coordinate_frame = mcstas *imgcif
        .type = choice
        .help = "Which coordinate system is being used to provide input vectors"
      # Make these two mutually exclusive ?
      n_images = None
        .type = int
        .help = "Number of blank images to be generated per file"
      n_events = None
        .type = int
        .help = "Length of event stream per file"
    }

    include scope nexgen.phil.goniometer_scope

    include scope nexgen.phil.beamline_scope

    include scope nexgen.phil.detector_scope
    """,
    process_includes=True,
)

# Parse command line arguments
parser = argparse.ArgumentParser(
    description="Parse parameters to generate a NeXus file."
)
parser.add_argument("--debug", action="store_const", const=True)
parser.add_argument("phil", nargs="*")


def main():
    # working_phil = master_phil.fetch()
    # working_phil.show()
    args = parser.parse_args()
    cl = master_phil.command_line_argument_interpreter()
    working_phil = master_phil.fetch(cl.process_and_fetch(args.phil))
    params = working_phil.extract()

    # Start logger
    logdir = os.path.dirname(params.output.master_file_name)
    logging.basicConfig(
        filename=os.path.join(logdir, "NeXusWriter.log"),
        format="%(message)s",
        level="DEBUG",
    )

    # Check that the file extension is correct
    ext = os.path.splitext(params.output.master_file_name)[1]
    assert (ext == ".nxs") or (
        ext == ".h5"
    ), "Wrong file extension, please pass a .h5 or .nxs file."


if __name__ == "__main__":
    # args = parser.parse_args()
    main()
