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
    * Still shots
    * Fixed target
    * 3D grid scan


Example usage
*************

**Example 1: grid scan on I24**

.. code-block:: python

    "This example calls the SSX writer for a fixed_target experiment on I24."

    from nexgen.beamlines.I24_Eiger_nxs import write_nxs
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

    write_nxs(
        visitpath="/path/to/dataset",
        filename="Expt1_00",
        exp_type="fixed_target",
        num_imgs=1600,
        beam_center=[beam_x, beam_y],
        det_dist=D,
        start_time=datetime.strptime("2022-09-09T14:19:27", "%Y-%m-%dT%H:%M:%S"),
        stop_time=datetime.now(),
        exp_time=t,
        transmission=1.,
        wavelength=0.67019,
        flux=None,
        pump_status="false",
        pump_exp=None,
        pump_delay=None,
        chip_info=chip_dict,
        chipmap="/path/to/chip.map/file",
    )



**Example 2: grid scan on I19-2 using Tristan10M**

.. code-block:: python

    "This example calls the SSX writer for a simple time-resolved pump-probe experiment using Tristan."

    from nexgen.beamlines.SSX_Tristan_nxs import write_nxs
    from datetime import datetime

    beam_x = 1590.7
    beam_y = 1643.7

    D = 0.5     # Detector distance passed in mm
    t = 0.002   # Exposure time passed in s

    write_nxs(
        visitpath="/path/to/dataset",
        filename="Expt1_00",
        location="I19",
        beam_center=[beam_x, beam_y],
        det_dist=D,
        start_time=datetime.now(),
        stop_time=None,
        exp_time=t,
        transmission=1.,
        wavelength=0.649,
        pump_status=True,
        pump_exp=3.0,
        pump_delay=1.0,
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
