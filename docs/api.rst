===
API
===

.. automodule:: nexgen
    :members:
    :show-inheritance:


Writing tools
=============

NXmx writers
------------

.. automodule:: nexgen.nxs_write.NXclassWriters
    :members:

All the writers above can be called using the ``call_writers`` function, with the exception of ``write_NXentry``, ``write_NXdatetime`` and ``write_NXnote``.  
NOTE: Versions >= 0.6.8 (current one) hopefully won't have these writers, and since there are no docs yet, the line above probably doesn't matter.

.. autofunction:: nexgen.nxs_write.NexusWriter.call_writers


Writing blank datasets
----------------------
**Generating blank images**

.. autofunction:: nexgen.tools.DataWriter.generate_image_files

Using an *Eiger* or *Tristan* detector mask ...

.. autofunction:: nexgen.tools.DataWriter.build_an_eiger

.. autofunction:: nexgen.tools.DataWriter.build_a_tristan

**Generating pseudo-events** 

.. autofunction:: nexgen.tools.DataWriter.generate_event_files

VDS writer
----------

.. autofunction:: nexgen.tools.VDS_tools.image_vds_writer

.. autofunction:: nexgen.tools.VDS_tools.vds_file_writer


Copying tools
=============

.. automodule:: nexgen.nex_copy.CopyNexus
    :members:

.. automodule:: nexgen.nxs_copy.CopyTristanNexus
    :members:


Utilities
=========

Checking for scan axes
----------------------

.. autofunction:: nexgen.nxs_write.NexusWriter.ScanReader

Generally useful tools
----------------------

.. automodule:: nexgen
    :members:

**Writing tools**

.. automodule:: nexgen.nxs_write
    :members:

**Copying tools**

.. automodule:: nexgen.nxs_copy
    :members:


HDF5 metafile reader
--------------------

Metafile definition:

.. automodule:: nexgen.tools.Metafile
    :members:
    :show-inheritance:

Reading the information stored in the metafile and copying it across to the new NeXus file:

.. autofunction:: nexgen.tools.MetaReader.overwrite_beam

.. autofunction:: nexgen.tools.MetaReader.overwrite_detector

GDA integration tools
---------------------

**Read geometry and detector parameters from GDA-generated JSON files**

.. autofunction:: nexgen.tools.GDAjson2params.read_geometry_from_json

.. autofunction:: nexgen.tools.GDAjson2params.read_detector_params_from_json

**Gather beamline and collection information from GDA-generated xml file**

.. autoclass:: nexgen.tools.ExtendedRequest.ExtendedRequestIO
    :members:

Logging configuration
---------------------

.. automodule:: nexgen.log
    :members: