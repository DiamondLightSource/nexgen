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


.. autofunction:: nexgen.beamlines.i19_2.basic_nxmx_writer


and


.. autofunction:: nexgen.beamlines.i19_2.serial_nexus_writer


can be called from python and will run the main i19 writer


.. autofunction:: nexgen.beamlines.i19_2.main_writer.main_writer_i19


which in turn calls one of the following depending on the specified detector type


.. autofunction:: nexgen.beamlines.i19_2.tristan.tristan_writer


.. autofunction:: nexgen.beamlines.i19_2.eiger.eiger_writer


Some useful type definitions to use with these methods:


.. autoclass:: nexgen.beamlines.i19_2.GonioAxisPosition
    :members:


.. autoclass:: nexgen.beamlines.i19_2.DetAxisPosition
    :members:


.. autoclass:: nexgen.beamlines.i19_2.DetectorName
    :members:


Collection parameters schema for I19-2


.. autopydantic_model:: nexgen.beamlines.i19_2.CollectionParams
    :inherited-members: BaseModel
    :model-show-config-summary: False


.. autopydantic_model:: nexgen.beamlines.i19_2.ExtraDetectorParams
    :inherited-members: BaseModel
    :model-show-config-summary: False



1. Interface with GDA ...


.. autofunction:: nexgen.beamlines.i19_2.gda_nexus_writer


Collection parameters schema for I19-2 from GDA


.. autopydantic_model:: nexgen.beamlines.i19_2.ParamsFromGDA
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
