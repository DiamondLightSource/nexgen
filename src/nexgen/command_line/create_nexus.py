"""
Command line tool to generate a NeXus file.
"""

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

    include scope nexgen.phil.goniometer_scope

    include scope nexgen.phil.beamline_scope

    include scope nexgen.phil.detector_scope
    """,
    process_includes=True,
)
