"""
Command line tool to generate a NeXus file.
"""

import h5py
import logging
import argparse
from pathlib import Path

import freephil

from nexgen import get_filename_template
from nexgen.nxs_write.NexusWriter import write_new_nexus

# from .. import get_filename_template
# from ..nxs_write.NexusWriter import write_new_nexus

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
        .help = "Application definition for NeXus file. Deafults to Nxmx."
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

    include scope nxs_phil.goniometer_scope

    include scope nxs_phil.beamline_scope

    include scope nxs_phil.detector_scope
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
    # data_file = (
    #    Path(data_file_template % 1).expanduser().resolve()
    # )  # assumes only one file
    data_file_list = [
        Path(data_file_template % (n + 1)).expanduser().resolve()
        for n in range(params.input.n_files)
    ]
    # TODO write more than one file (and add vds if prompted)

    # Add some information to logger
    logger.info("NeXus file will be saved as %s" % params.output.master_file_name)
    logger.info("Data file(s) template: %s" % data_file_template)
    logger.info(
        "%d file(s) containing blank data to be written." % params.input.n_files
    )

    # Next: go through technical info (goniometer, detector, beamline etc ...)
    cf = params.input.coordinate_frame
    goniometer = params.goniometer
    detector = params.detector
    module = params.module
    source = params.source
    beam = params.beam
    attenuator = params.attenuator

    # Log information
    logger.info("Data type: %s" % detector.mode)

    logger.info("Source information")
    logger.info(f"Facility: {source.name} - {source.type}.")
    logger.info(f"Beamline: {source.beamline_name}")

    logger.info("Coordinate system: %s" % cf)
    if cf == "imgcif":
        logger.warning(
            "Input coordinate frame is imgcif. They will be converted to mcstas."
        )

    logger.info("Goniometer information")
    axes = goniometer.axes
    axis_vectors = goniometer.vectors

    for tu in zip(goniometer.types, goniometer.units):
        assert tu in (("translation", "mm"), ("rotation", "deg"))

    assert len(axis_vectors) == 3 * len(axes)

    for j in reversed(range(len(axes))):
        vector = axis_vectors[3 * j : 3 * j + 3]
        print(
            f"Goniometer axes: {axes[j]} => {vector} ({goniometer.types[j]}) on {goniometer.depends[j]}"
        )

    for ax, dep, t, u, j in zip(
        goniometer.axes,
        goniometer.depends,
        goniometer.types,
        goniometer.units,
        range(len(goniometer.axes)),
    ):
        vector = goniometer.vectors[3 * j : 3 * j + 3]
        offset = goniometer.offsets[3 * j : 3 * j + 3]
        logger.info(
            "%s %s %s %s %s %s %s %s %s"
            % (
                ax,
                dep,
                t,
                u,
                vector,
                offset,
                goniometer.starts[j],
                goniometer.ends[j],
                goniometer.increments[j],
            )
        )

    logger.info("")

    logger.info("Detector information: %s" % detector.description)
    logger.info(
        f"Sensor made of {detector.sensor_material} x {detector.sensor_thickness}mm"
    )
    if detector.mode == "images":
        logger.info(f"Trusted pixels > {detector.underload} and < {detector.overload}")
    logger.info(
        f"Image is a {detector.image_size} array of {detector.pixel_size} mm pixels"
    )

    logger.info("Detector axes:")
    axes = detector.axes
    axis_vectors = detector.vectors
    for tu in zip(detector.types, detector.units):
        assert tu in (("translation", "mm"), ("rotation", "deg"))

    assert len(axis_vectors) == 3 * len(axes)

    for j in range(len(axes)):
        vector = axis_vectors[3 * j : 3 * j + 3]
        print(f"Detector axis: {axes[j]} => {vector}")

    if detector.flatfield is None:
        logger.info("No flatfield applied")
    else:
        logger.info(f"Flatfield correction data lives here {detector.flatfield}")

    if detector.pixel_mask is None:
        logger.info("No bad pixel mask for this detector")
    else:
        logger.info(f"Bad pixel mask lives here {detector.pixel_mask}")

    logger.info("Module information")
    logger.warning(f"module_offset field setting: {module.module_offset}")
    logger.info(f"Number of modules: {module.num_modules}")
    logger.info(f"Fast axis at datum position: {module.fast_axis}")
    logger.info(f"Slow_axis at datum position: {module.slow_axis}")
    logger.info("")

    with h5py.File(master_file, "x") as nxsfile:
        write_new_nexus(
            nxsfile,
            data_file_list,
            params.input,
            goniometer,
            detector,
            module,
            source,
            beam,
            attenuator,
        )

    logger.info("==" * 50)


if __name__ == "__main__":
    main()
