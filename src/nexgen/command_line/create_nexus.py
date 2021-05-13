"""
Command line tool to generate a NeXus file.
"""

# import sys

# sys.path.append("/home/uhz96441/local/Python3_dials/modules/nexgen/src/nexgen/")

# import h5py
import logging
import argparse
from pathlib import Path

import freephil

# import nexgen.phil
from nexgen.data import get_filename_template

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
      coordinate_frame = *mcstas imgcif
        .type = choice
        .help = "Which coordinate system is being used to provide input vectors"
      n_files = 1
        .type = int
        .help = "Number of data files to write - defaults to 1."
      # Make these two mutually exclusive ?
      n_images = None
        .type = int
        .help = "Number of blank images to be generated per file"
      n_events = None
        .type = int
        .help = "Length of event stream per file"
      write_vds = False
        .type = bool
        .help = "If True, create also a _vds.h5 file. Only for image data."
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
parser.add_argument(
    "-c",
    "--show-config",
    action="store_true",
    default=False,
    dest="show_config",
    help="Show the configuration parameters.",
)
parser.add_argument("phil_args", nargs="*")


def main():
    # working_phil = master_phil.fetch()
    # working_phil.show()
    args = parser.parse_args()
    cl = master_phil.command_line_argument_interpreter()
    working_phil = master_phil.fetch(cl.process_and_fetch(args.phil_args))
    params = working_phil.extract()

    # Path to file
    master_file = Path(params.output.master_file_name).expanduser().resolve()
    # Start logger
    logfile = master_file.parent / "NeXusWriter.log"
    logging.basicConfig(
        filename=logfile.as_posix(),
        format="%(message)s",
        level="DEBUG",
    )

    # Check that the file extension is correct
    assert (master_file.suffix == ".nxs") or (
        master_file.suffix == ".h5"
    ), "Wrong file extension, please pass a .h5 or .nxs file."

    # Get data file name template
    data_file_template = get_filename_template(master_file)
    print(data_file_template)


if __name__ == "__main__":
    # args = parser.parse_args()
    main()
