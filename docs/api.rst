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

.. autofunction:: nexgen.nxs_write.NexusWriter.call_writers

.. autofunction:: nexgen.nxs_write.NexusWriter.write_nexus_from_scope

Writing blank datasets
----------------------

Generating blank images
^^^^^^^^^^^^^^^^^^^^^^^

Using an *Eiger* or *Tristan* detector mask ...

.. autofunction:: nexgen.tools.DataWriter.build_an_eiger

.. autofunction:: nexgen.tools.DataWriter.build_a_tristan



.. autofunction:: nexgen.tools.DataWriter.generate_image_files


Generating pseudo-events
^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: nexgen.tools.DataWriter.pseudo_event_list



.. autofunction:: nexgen.tools.DataWriter.generate_event_files


VDS writer
----------

.. automodule:: nexgen.tools.VDS_tools
    :members:


Copying tools
=============

.. automodule:: nexgen.nex_copy.CopyNexus
    :members:

.. automodule:: nexgen.nxs_copy.CopyTristanNexus
    :members:


.. automodule:: nexgen.nxs_copy
    :members:


Utilities
=========

.. automodule:: nexgen
    :members:

**Writing tools**

.. automodule:: nexgen.nxs_write
    :members:

**Copying tools**

.. automodule:: nexgen.nxs_copy
    :members:


Finding the scan axes
---------------------

.. autofunction:: nexgen.nxs_write.NexusWriter.ScanReader


HDF5 metafile reader
--------------------

Metafile definition:

.. automodule:: nexgen.tools.Metafile
    :members:
    :show-inheritance:


A couple of functions are available for reading the information stored in the metafile and copying it across to the new NeXus file:

.. autofunction:: nexgen.tools.MetaReader.overwrite_beam

.. autofunction:: nexgen.tools.MetaReader.overwrite_detector


Logging configuration
=====================

.. automodule:: nexgen.log
    :members:


DLS beamlines
=============

I19-2
-----

TODO. Just a thought. move read_from_xml to either extended request or the GDA tools (in this case maybe rename?) and modify the
I19-2 script with an option that either writes from GDA or does the same as I24 bypassing that completely. 

.. autofunction:: nexgen.beamlines.I19_2_nxs.tristan_writer

.. autofunction:: nexgen.beamlines.I19_2_nxs.eiger_writer

I24
---

TODO. Namedtuple thing

.. autofunction:: nexgen.beamlines.I24_Eiger_nxs.extruder

.. autofunction:: nexgen.beamlines.I24_Eiger_nxs.fixed_target

SSX using Tristan Detector
--------------------------

TODO. Another thought. Considering the idea of having Tristan on I24 this should be usable from both beamlines.
I mean... it should only be a matter of switching the name? I can be easily passed as input argument ...

.. autofunction:: nexgen.beamlines.SSX_Tristan_nxs.write_nxs

GDA integration tools
---------------------

Read geometry and detector parameters from GDA-generated JSON files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: nexgen.tools.GDAjson2params.read_geometry_from_json

.. autofunction:: nexgen.tools.GDAjson2params.read_detector_params_from_json

Gather beamline and collection information from GDA-generated xml file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: nexgen.tools.ExtendedRequest.ExtendedRequestIO
    :members:
