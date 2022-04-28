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

GDA integration tools
---------------------
(or whatever)