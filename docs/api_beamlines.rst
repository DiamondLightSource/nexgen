=============
Beamlines API
=============

General utilities
-----------------

.. autoclass:: nexgen.beamlines.beamline_utils.BeamlineAxes
    :members:


.. autoclass:: nexgen.beamlines.beamline_utils.PumpProbe
    :members:

I19-2
-----

Directly from the python intepreter/ a python script ...

.. autoclass:: nexgen.beamlines.I19_2_nxs.tr_collect
    :members:


The function

.. autofunction:: nexgen.beamlines.I19_2_nxs.nexus_writer


can be called from python and depending on the specified detector type will run:


.. autofunction:: nexgen.beamlines.I19_2_nxs.tristan_writer

.. autofunction:: nexgen.beamlines.I19_2_nxs.eiger_writer

Interface with GDA ...

.. autoclass:: nexgen.beamlines.I19_2_gda_nxs.tr_collect
    :members:

.. autofunction:: nexgen.beamlines.I19_2_gda_nxs.tristan_writer

.. autofunction:: nexgen.beamlines.I19_2_gda_nxs.eiger_writer


Serial crystallography: Eiger writers
-------------------------------------

.. autofunction:: nexgen.beamlines.SSX_Eiger_nxs.ssx_eiger_writer

Serial crystallography: Tristan writers
---------------------------------------

.. autofunction:: nexgen.beamlines.SSX_Tristan_nxs.ssx_tristan_writer


Serial crystallography: chip tools
----------------------------------

.. automodule:: nexgen.beamlines.SSX_chip
    :members:


Serial crystallography: experiment types
----------------------------------------

.. autofunction:: nexgen.beamlines.SSX_expt.run_extruder

.. autofunction:: nexgen.beamlines.SSX_expt.run_fixed_target


GDA integration tools
---------------------

Read geometry and detector parameters from GDA-generated JSON files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nexgen.beamlines.GDAtools.GDAjson2params


.. autoclass:: nexgen.beamlines.GDAtools.GDAjson2params.JSONParamsIO
    :members:


Gather beamline and collection information from GDA-generated xml file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: nexgen.beamlines.GDAtools.ExtendedRequest
    :members:
