===========================
Beamline specific utilities
===========================


Nexgen is currently being used for some specific applications at beamlines I19-2 and I24 at DLS.

Time resolved collections on I19-2
----------------------------------

For completeness' sake there is also an option to write a NeXus file for an Eiger detector.
(nexgen was actually born out of a need to write the nxs file for tristan expt)


Serial crystallography
----------------------

I19-2: Tristan and Eiger nexus file writing, SSX with tristan detector.
I24: serial crystallography -> still shots (extruder application), fixed target (TR or not), 3d scan (tbc)



Example usage
*************

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


=============
Beamlines API
=============

I19-2
-----

Directly from the beamline ...

.. autoclass:: nexgen.beamlines.I19_2_nxs.tr_collect
    :members:

.. autofunction:: nexgen.beamlines.I19_2_nxs.tristan_writer

.. autofunction:: nexgen.beamlines.I19_2_nxs.eiger_writer

From GDA ...

.. autoclass:: nexgen.beamlines.I19_2_gda_nxs.tr_collect
    :members:

.. autofunction:: nexgen.beamlines.I19_2_gda_nxs.tristan_writer

.. autofunction:: nexgen.beamlines.I19_2_gda_nxs.eiger_writer


I24
---

.. autoclass:: nexgen.beamlines.I24_Eiger_nxs.ssx_collect
    :members:

.. autofunction:: nexgen.beamlines.I24_Eiger_nxs.extruder

.. autofunction:: nexgen.beamlines.I24_Eiger_nxs.fixed_target


SSX using Tristan Detector
--------------------------

.. autoclass:: nexgen.beamlines.SSX_Tristan_nxs.ssx_tr_collect
    :members:

.. autofunction:: nexgen.beamlines.SSX_Tristan_nxs.write_nxs



GDA integration tools
---------------------

Read geometry and detector parameters from GDA-generated JSON files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: nexgen.beamlines.GDAtools.GDAjson2params.read_geometry_from_json

.. autofunction:: nexgen.beamlines.GDAtools.GDAjson2params.read_detector_params_from_json

Gather beamline and collection information from GDA-generated xml file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: nexgen.tools.ExtendedRequest.ExtendedRequestIO
    :members:
