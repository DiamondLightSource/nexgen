"""
Command line tool to generate a NeXus file.
"""

# import sys

# sys.path.append("/home/uhz96441/local/Python3_dials/modules/nexgen/src/nexgen/")
import freephil

master_phil = freephil.parse(
    """
    output {
      data_file_template = nexus_%06d.h5
        .type = path
        .help = "Filename template for data files"
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

    include scope phil.goniometer_scope

    include scope phil.beamline_scope

    include scope phil.detector_scope
    """,
    process_includes=True,
)


def main():
    working_phil = master_phil.fetch()
    working_phil.show()
    # params = working_phil.extract()


if __name__ == "__main__":
    main()
