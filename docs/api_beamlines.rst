=============
Beamlines API
=============

General utilities
-----------------

.. autoclass:: nexgen.beamlines.beamline_utils.BeamlineAxes
    :members:


.. autopydantic_model:: nexgen.beamlines.beamline_utils.GeneralParams
    :model-show-config-summary: False


.. autopydantic_model:: nexgen.beamlines.beamline_utils.PumpProbe
    :model-show-config-summary: False

I19-2
-----

1. Directly from the python intepreter/ a python script ...

The functions


.. autofunction:: nexgen.beamlines.I19_2_nxs.nexus_writer


and


.. autofunction:: nexgen.beamlines.I19_2_nxs.serial_nexus_writer


can be called from python and depending on the specified detector type will run:


.. autofunction:: nexgen.beamlines.I19_2_nxs.tristan_writer


.. autofunction:: nexgen.beamlines.I19_2_nxs.eiger_writer


Some useful type definitions to use with these methods:


.. autoclass:: nexgen.beamlines.I19_2_nxs.GonioAxisPosition
    :members:


.. autoclass:: nexgen.beamlines.I19_2_nxs.DetAxisPosition
    :members:


.. autoclass:: nexgen.beamlines.I19_2_nxs.DetectorName
    :members:


Collection parameters schema for I19-2


.. autopydantic_model:: nexgen.beamlines.I19_2_nxs.CollectionParams
    :inherited-members: BaseModel
    :model-show-config-summary: False



2. Interface with GDA ...


.. autofunction:: nexgen.beamlines.I19_2_gda_nxs.tristan_writer


.. autofunction:: nexgen.beamlines.I19_2_gda_nxs.eiger_writer


Collection parameters schema for I19-2 from GDA


.. autopydantic_model:: nexgen.beamlines.I19_2_gda_nxs.GDACollectionParams
    :inherited-members: BaseModel
    :model-show-config-summary: False


Serial crystallography with Eiger on I24
----------------------------------------


.. autofunction:: nexgen.beamlines.SSX_Eiger_nxs.ssx_eiger_writer


Collection parameters schema for SSX


.. autopydantic_model:: nexgen.beamlines.SSX_Eiger_nxs.SerialParams
    :inherited-members: BaseModel
    :model-show-config-summary: False



Serial crystallography: chip tools
----------------------------------

.. automodule:: nexgen.beamlines.SSX_chip
    :members:


Serial crystallography: experiment types
----------------------------------------

.. autofunction:: nexgen.beamlines.SSX_expt.run_extruder

.. autofunction:: nexgen.beamlines.SSX_expt.run_fixed_target


Electron diffraction: Singla writer
-----------------------------------

.. autofunction:: nexgen.beamlines.ED_singla_nxs.singla_nexus_writer


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
