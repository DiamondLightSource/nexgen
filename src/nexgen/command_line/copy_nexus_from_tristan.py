"""
Command line tool to copy metadata from LATRD Tristan data collection to a new nexus file.
"""

import os
import sys

import freephil

from nexgen.copy import CopyTristanNexus

tristan_scope = freephil.parse(
    """
    input {
      data_file = None
        .type = path
        .help = "HDF5 file containing the newly binned images."
      tristan_nexus_file = None
        .type = path
        .help = "NeXus file with experiment metadata to be copied."
      experiment_type = *single multiple pump-probe
        .type = choice
        .help = "Define the type of experiment that has been run."
      angular_velocity = 0.1
        .type = float
        .help = "Angular velocity of sample rotation, in deg/s "
      mode = *static rotation
        .type = choice
        .help = "For pump-probe experiments, define whether it's a rotation or not."
    }
    """
)


def main():
    args = sys.argv[1:]
    clai = tristan_scope.command_line_argument_interpreter()
    working = tristan_scope.fetch(clai.process_and_fetch(args))
    params = working.extract()

    print(
        f"Create a NeXus file to go with images binned from LATRD Tristan detector event data."
    )
    wdir = os.path.dirname(params.input.data_file)
    data_file_name = os.path.basename(params.input.data_file)
    print(f"Working directory: {wdir}")
    print(f"Image data file name: {data_file_name}")
    print(f"Original Tristan NeXus file: {params.input.tristan_nexus_file}")

    print(f"Experiment type: {params.input.experiment_type}")
    if params.input.experiment_type == "single":
        print("A single images binned from all the events.")
        CopyTristanNexus.single_image_nexus(
            params.input.data_file, params.input.tristan_nexus_file
        )
    elif params.input.experiment_type == "multiple":
        print("Rotation dataset.")
        print("Angular velocity: %.2f deg/s" % params.input.angular_velocity)
        CopyTristanNexus.multiple_images_nexus(
            params.input.data_file,
            params.input.tristan_nexus_file,
            params.input.angular_velocity,
        )
    elif params.input.experiment_type == "pump-probe":
        print("Pump-probe experiment.")
        print(f"Mode: {params.input.mode}")
        CopyTristanNexus.pump_probe_nexus(
            params.input.data_file, params.input.tristan_nexus_file, params.input.mode
        )
    else:
        sys.exit(f"Please pass a valid experiment type.")
    print("All done!")


if __name__ == "__main__":
    main()
