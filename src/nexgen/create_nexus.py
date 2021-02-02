import os
import sys
import logging
import h5py

from geometry_phil import scope
from writer import NexusWriter

logger = logging.getLogger("NXSWriter")


def main():
    args = sys.argv[1:]
    clai = scope.command_line_argument_interpreter()
    working = scope.fetch(clai.process_and_fetch(args))
    params = working.extract()

    logdir = os.path.dirname(params.output.master_file_name)
    logging.basicConfig(
        filename=os.path.join(logdir, "NexusWriter.log"),
        format="%(message)s",
        level="DEBUG",
    )

    ext = os.path.splitext(params.output.master_file_name)[1]
    print(ext)
    # assert (
    #    (ext == ".nxs") or (ext == ".h5")
    # ), "Wrong file extension, please pass a .h5 or .nxs file."
    # assert (
    #    os.path.splitext(params.output.data_file_template) == ".h5"
    # ), "Wrong file extension, please pass a .h5 or .nxs file."

    logger.info("Nexus file name %s" % params.output.master_file_name)
    cf = params.input.coordinate_frame
    logger.info("Coordinate system: %s" % cf)
    if cf == "imgcif":
        logger.warning("Coordinates will be converted to mcstas.")

    print("Detector information:")
    d = params.input.detector
    print(d.description)
    print(f"Sensor made of {d.sensor_material} x {d.sensor_thickness}mm")
    print(f"Trusted pixels > {d.underload} and < {d.overload}")
    print(f"Image is a {d.image_size} array of {d.pixel_size} mm pixels")

    logger.info("Data type: %s" % d.mode)
    logger.info("")

    logger.info("Detector information: %s" % d.description)
    logger.info(f"Sensor made of {d.sensor_material} x {d.sensor_thickness}mm")
    if d.mode == "images":
        logger.info(f"Trusted pixels > {d.underload} and < {d.overload}")
    logger.info(f"Image is a {d.image_size} array of {d.pixel_size} mm pixels")

    logging.info("Axes:")
    for ax, dep, t, u, j in zip(
        d.axes, d.depends, d.types, d.units, range(len(d.axes))
    ):
        vector = d.vectors[3 * j : 3 * j + 3]
        logger.info("%s %s %s %s %s %s" % (ax, dep, t, u, vector, d.starts[j]))

    if d.flatfield is None:
        logger.info("No flatfield applied")
    else:
        logger.info(f"Flatfield correction data lives here {d.flatfield}")

    if d.pixel_mask is None:
        logger.info("No bad pixel mask for this detector")
    else:
        logger.info(f"Bad pixel mask lives here {d.pixel_mask}")

    logger.warning(f"module_offset field setting: {d.module_offset}")
    logger.info("")

    axes = d.axes
    axis_vectors = d.vectors

    # one day other units could be legal.. but check things match up
    for tu in zip(d.types, d.units):
        assert tu in (("translation", "mm"), ("rotation", "deg"))

    assert len(axis_vectors) == 3 * len(axes)

    for j in range(len(axes)):
        vector = axis_vectors[3 * j : 3 * j + 3]
        print(f"Detector axis: {axes[j]} => {vector}")

    print("Goniometer information:")

    g = params.input.goniometer
    axes = g.axes
    axis_vectors = g.vectors

    for tu in zip(g.types, g.units):
        assert tu in (("translation", "mm"), ("rotation", "deg"))

    assert len(axis_vectors) == 3 * len(axes)

    for j in reversed(range(len(axes))):
        vector = axis_vectors[3 * j : 3 * j + 3]
        print(
            f"Goniometer axis: {axes[j]} => {vector} ({g.types[j]}) on {g.depends[j]}"
        )

    logger.info("Goniometer information")
    for ax, dep, t, u, j in zip(
        g.axes, g.depends, g.types, g.units, range(len(g.axes))
    ):
        vector = g.vectors[3 * j : 3 * j + 3]
        offset = g.offsets[3 * j : 3 * j + 3]
        logger.info(
            "%s %s %s %s %s %s %s %s %s"
            % (ax, dep, t, u, vector, offset, g.starts[j], g.ends[j], g.increments[j])
        )

    logger.info("")

    with h5py.File(params.output.master_file_name, "w") as nxsfile:
        NexusWriter(nxsfile, params).write()

    logger.info("==" * 50)


if __name__ == "__main__":
    main()
