===========================
Beamline specific utilities
===========================


Nexgen is currently being used for some specific applications at beamlines I19-2 and I24 at DLS.

Time resolved collections on I19-2
----------------------------------

Where GDA is not in use, a NXmx format NeXus files writer is available for time-resolved
Eiger/Tristan collections.


Example usage
*************

**Example I: Rotation scan with Tristan**

.. code-block:: python

    """
    This example calls the nexus writer for a collection using Tristan detector.

    Note that in this case the axes start and end positions need to be passed to the writer
    and this can be done by defining the following namedtuples:
       axes = namedtuple("axes", ("id", "start", "end"))
        det_axes = namedtuple("det_axes", ("id", "start"))
    """

    from nexgen.beamlines.I19_2_nxs import nexus_writer

    from datetime import datetime
    from collections import namedtuple
    from pathlib import Path

    axes = namedtuple("axes", ("id", "start", "end"))
    det_axes = namedtuple("det_axes", ("id", "start"))

    axes_list = [
        axes("omega", 0, 10),
        axes("kappa", 0, 0),
        axes("phi", -90, -90),
        axes("sam_z", 0, 0),
        axes("sam_y", 1, 1),
        axes("sam_x", 0, 0),
    ]

    det_ax_list = [
        det_axes("two_theta", 90),
        det_axes("det_z", 100),
    ]

    nexus_writer(
        meta_file=Path("/path/to/file_meta.h5"),
        detector_name="tristan",
        scan_axis="omega",
        start_time=datetime.now(),
        exposure_time=60.0,
        transmission=1.0,
        wavelength=0.6,
        beam_center=[1000., 1200.],
        gonio_pos=axes_list,
        det_pos=det_ax_list,
    )



**Example II: Rotation scan with Eiger**

.. code-block:: python

    """
    This example calls the nexus writer for a collection using Eiger detector.

    Note that in this case there's no need to pass the axes positions as those can be read from
    the config written to the _meta.h5 file at the arming of the detector.
    """

    from nexgen.beamlines.I19_2_nxs import nexus_writer

    from datetime import datetime
    from pathlib import Path

    nexus_writer(
        meta_file=Path("/path/to/file_meta.h5"),
        detector_name="eiger",
        scan_axis="phi",
        start_time=datetime.now(),
        exposure_time=60.0,
        transmission=1.0,
        wavelength=0.6,
        beam_center=[1000., 1200.],
    )



Serial crystallography
----------------------

- I19-2: Fixed target SSX with Tristan detector.
- I24: serial crystallography with Eiger detector
    * Still shots (or extruder)
    * Fixed target
    * 3D grid scan


Example usage
*************

**Example 1: grid scan on I24**

.. code-block:: python

    "This example calls the SSX writer for a fixed_target experiment on I24."

    from nexgen.beamlines.I24_Eiger_nxs import ssx_eiger_writer
    from datetime import datetime

    beam_x = 1590.7
    beam_y = 1643.7

    D = 1.480   # Detector distance passed in mm
    t = 0.01    # Exposure time passed in s

    # Example of chip_dict (form beamline I24) with minimum required values needed for goniometer computations.
    chip_dict = {
        'X_NUM_STEPS':    [11, 20],
        'Y_NUM_STEPS':    [12, 20],
        'X_STEP_SIZE':    [13, 0.125],
        'Y_STEP_SIZE':    [14, 0.125],
        'X_START':        [16, 0],
        'Y_START':        [17, 0],
        'Z_START':        [18, 0],
        'X_NUM_BLOCKS':   [20, 8],
        'Y_NUM_BLOCKS':   [21, 8],
        'X_BLOCK_SIZE':   [24, 3.175],
        'Y_BLOCK_SIZE':   [25, 3.175],
        'N_EXPOSURES':    [30, 1],
        'PUMP_REPEAT':    [32, 0],
    }

    ssx_eiger_writer(
        "/path/to/dataset",     # visitpath
        "Expt1_00",    # filename root
        "I24",      # beamline
        "fixed_target",     # experiment type
        pump_status=True,
        num_imgs=1600,
        beam_center=[beam_x, beam_y],
        det_dist=D,
        start_time=datetime.strptime("2022-09-09T14:19:27", "%Y-%m-%dT%H:%M:%S"),
        stop_time=datetime.now(),
        exp_time=t,
        transmission=1.,
        wavelength=0.67019,
        flux=None,
        pump_exp=None,
        pump_delay=0.001,
        chip_info=chip_dict,
        chipmap="/path/to/chip.map/file",
    )



**Example 2: grid scan on I19-2 using Tristan10M**

.. code-block:: python

    "This example calls the SSX writer for a simple time-resolved pump-probe experiment on a full chip using Tristan."

    from nexgen.beamlines.SSX_Tristan_nxs import ssx_tristan_writer
    from datetime import datetime

    beam_x = 1590.7
    beam_y = 1643.7

    D = 0.5     # Detector distance passed in mm
    t = 0.002   # Exposure time passed in s

    write_nxs(
        "/path/to/dataset",
        "Expt1_00",
        "I19-2",
        exp_time=t,
        det_dist=D,
        beam_center=[beam_x, beam_y],
        transmission=1.,
        wavelength=0.649,
        start_time=datetime.now(),
        stop_time=None,
        chip_info=chip_dict,
        chipmap=None,
    )


I19-2 CLI
---------

Example usage
*************

Write a NeXus file for a Tristan collection using a GDA-generated xml file containing the beamline information:

.. code-block:: console

    I19_nexus 1 Expt_00_meta.h5 Expt.xml tristan 300 0.649 1590.7 1643.7 --start 2022-09-09T10:26:32Z --stop 2022-09-09T10:31:32Z


Manually generate a NeXus file for a dataset collected on Eiger detector using the metadata recorded inside the meta file:

.. code-block:: console

    I19_nexus 2 Expt1_00_meta.h5 eiger 0.02 -tr 100 --use-meta


If the `--use-meta` flag is not passed, the writer will not look up the axes/beam_center/wavelength information in the meta file.
This will then need to be passed from the commang line:

.. code-block:: console

    I19_nexus gen Expt1_00_meta.h5 eiger 0.095 -wl 0.485 -bc 989.8 1419 --det-axes det_z --det-start 140 --axes omega phi --ax-start -90 -130.5 --ax-inc 0 0.1 -tr 5 -n 75


.. note::
    Only the goniometer/detector axes that have values and increments different from 0 need to be passed to the command line.
    If --scan-axis is not passed, it will default to 'phi'.
    If -bc (beam_center) is not passed, in the absence of a meta file it will default to (0, 0)


SSX CLI
-------

Example usage
*************

Write a NeXus file for a serial collection on Eiger detector on beamline I24 at DLS:

.. code-block:: console

    SSX_nexus eiger dummy_00_meta.h5 I24 fixed-target 1600 -det 500 -tr 1.0 -wl 0.649 -bc 1590.7 1643.7 -e 0.002 -p --chipmap testchip.map