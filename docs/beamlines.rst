===========================
Beamline specific utilities
===========================


Nexgen is currently being used for some specific applications at beamlines I19-2 and I24 at DLS.

Time resolved collections on I19-2
----------------------------------

- NXmx format NeXus files writer for manual Eiger/Tristan collections (where GDA is not in use).
- Interface with GDA to write new NeXus files for a time-resolved experiment.

Serial crystallography
----------------------

- I19-2: Fixed target SSX with Tristan detector.
- I24 serial crystallography with Eiger detector:
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

    I19_nexus Expt_00_meta.h5 Expt.xml tristan 300 0.649 1590.7 1643.7 --start 2022-09-09T10:26:32Z --stop 2022-09-09T10:31:32Z


Manually generate a NeXus file for a dataset collected on Eiger detector using the metadata recorded inside the meta file:

.. code-block:: console

    I19-2_nxs Expt1_00_meta.h5 eiger 0.02 -tr 100


SSX CLI
-------

Example usage
*************

Write a NeXus file for a serial collection on Eiger detector on beamline I24 at DLS:

.. code-block:: console

    SSX_nexus eiger dummy_00_meta.h5 I24 fixed-target 1600 -det 500 -tr 1.0 -wl 0.649 -bc 1590.7 1643.7 -e 0.002 -p --chipmap testchip.map