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

    Note that in this case the axes start and end positions need to be passed to the writer.
    """

    from nexgen.beamlines.I19_2_nxs import (
        nexus_writer,
        GonioAxisPosition,
        DetAxisPosition,
        DetectorName
    )

    from datetime import datetime
    from pathlib import Path


    axes_list = [
        GonioAxisPosition(id="omega", start=0, end=10),
        GonioAxisPosition(id="kappa", start=0, end=0),
        GonioAxisPosition(id="phi", start=-90, end=-90),
        GonioAxisPosition(id="sam_z", start=0, end=0),
        GonioAxisPosition(id="sam_y", start=1, end=1),
        GonioAxisPosition(id="sam_x", start=0, end=0),
    ]

    det_ax_list = [
        DetAxisPosition(id="two_theta", start=90),
        DetAxisPosition(id="det_z", start=100),
    ]

    params = {
        "exposure_time"=60.0,
        "beam_center"=[1000., 1200.],
        "wavelength"=0.6,
        "transmission"=1.0,
        "detector_name"=DetectorName.TRISTAN,
        "metafile"=Path("/path/to/file_meta.h5"),
        "scan_axis"="omega",
        "axes_pos"=axes_list,
        "det_pos"=det_ax_list,
    }

    master_file=Path("/path/to/file.nxs")


    nexus_writer(
        params=params,
        master_file=master_file,
        timestamps=(datetime.now(), None),
    )



**Example II: Rotation scan with Eiger**

.. code-block:: python

    """
    This example calls the nexus writer for a collection using Eiger detector.

    Note that in this case there's no need to pass the axes positions as those can be read from
    the config written to the _meta.h5 file at the arming of the detector. In order to do this
    the use_meta flag must be passed as True.
    """

    from nexgen.beamlines.I19_2_nxs import nexus_writer, DetectorName

    from datetime import datetime
    from pathlib import Path

    params = {
        "exposure_time"=0.01,
        "beam_center"=[1000., 1200.],
        "wavelength"=0.6,
        "transmission"=1.0,
        "detector_name"=DetectorName.EIGER,
        "metafile"=Path("/path/to/file_meta.h5"),
        "scan_axis"="phi",
    }

    master_file=Path("/path/to/file.nxs")

    nexus_writer(
        params=params,
        master_file=master_file,
        timestamps=(datetime.now(), None),
        use_meta=True,
    )



**Example III: Serial collection with Eiger**

.. code-block:: python

    """
    This example calls the nexus writer for a serial collection with a small rotation at each well
    using Eiger detector.

    Note that in this the use_meta tag will be passed as false and the axes positions given explicitely
    to be able to give the correct values for each well.
    """

    from nexgen.beamlines.I19_2_nxs import (
        serial_nexus_writer,
        GonioAxisPosition,
        DetAxisPosition,
        DetectorName,
    )

    from datetime import datetime
    from pathlib import Path

    well_number = 800
    
    metafile = Path("/path/to/file_meta.h5")
    master_template = "/path/to/file_w%0{3}d.nxs"
    master_file = Path(master_template % (well_number))

    axes_list = [
        GonioAxisPosition(id="phi", start=-2.5, inc=0.2),
        GonioAxisPosition(id="kappa", start=0.005),
        GonioAxisPosition(id="omega", start=-90),
        GonioAxisPosition(id="sam_x", start=0.154),
        GonioAxisPosition(id="sam_y", start=0.0),
        GonioAxisPosition(id="sam_z", start=0.77)
    ]

    det_list = [
        DetAxisPosition(id="two_theta", start=0),
        DetAxisPosition(id="det_z", start=85)
    ]

    params = {
        "exposure_time"=0.1,
        "beam_center"=[1000., 1200.],
        "wavelength"=0.4,
        "transmission"=10,
        "detector_name"=DetectorName.EIGER,
        "metafile"=metafile,
        "tot_num_imgs"=900,
        "scan_axis"="phi",
        "axes_pos"=axes_list,
        "det_pos"=det_list,
    }

    serial_nexus_writer(
        params,
        master_file,
        (datetime.now(), None),
        use_meta=False,
        vds_offset=800,
        n_frames=25,
    )



Serial crystallography
----------------------

- I24: serial crystallography with Eiger detector
    * Still shots (or extruder)
    * Fixed target
    * 3D grid scan


Example usage
*************

**Example: grid scan on I24**

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


The full options for the I19 command line tool can be visualised by:

.. code-block:: console

    I19_nexus 2 --help


SSX CLI
-------

Example usage
*************

Write a NeXus file for a serial collection on Eiger detector on beamline I24 at DLS:

.. code-block:: console

    SSX_nexus eiger dummy_00_meta.h5 I24 fixed-target 1600 -det 500 -tr 1.0 -wl 0.649 -bc 1590.7 1643.7 -e 0.002 -p --chipmap testchip.map