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
      definition = Nxmx
        .type = str
        .h5lp = "Application definition for NeXus file. Deafults to Nxmx."
      n_files = 1
        .type = int
        .help = "Number of data files to write - defaults to 1."
      # Make these two mutually exclusive ?
      n_images = None
        .type = int
        .help = "Number of blank images to be written per file"
      n_events = None
        .type = int
        .help = "Size of event stream per file"
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
# FIXME .multiple doesn't seem to work (not an argparse problem)
# TODO consider adding write mode as optional argument
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
    # Just in case ...
    if master_file.suffix == ".h5":
        assert "master" in master_file.name, "Please pass a _master.h5 or .nxs file."

    # Get data file name template
    data_file_template = get_filename_template(master_file)
    # I need also an option to create a file with a link to existing data!

    # Add some information to logger
    logger.info("NeXus file will be saved as %s" % params.output.master_file_name)
    logger.info("Data file(s) template: %s" % data_file_template)
    logger.info(
        "%d file(s) containing blank data to be written." % params.input.n_files
    )

    # Next: go through technical info (goniometer, detector, beamline etc ...)
    # source = params.source
    # beam = params.beam
    # attenuator = params.attenuator
    # cf = params.input.coordinate_frame
    # goniometer = params.goniometer
    # detector = params.detector
    # module = params.module


if __name__ == "__main__":
    # args = parser.parse_args()
    main()
