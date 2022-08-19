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

