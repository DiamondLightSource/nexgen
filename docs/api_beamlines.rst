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


Serial crystallography: chip tools
----------------------------------

.. automodule:: nexgen.beamlines.SSX_chip
    :members:


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
