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

For a standard NXmx data collection, the NXclass writers can be called using the ``call_writers`` function, with the exception of ``write_NXentry``, ``write_NXdatetime`` and ``write_NXnote``.

.. autofunction:: nexgen.nxs_write.NexusWriter.call_writers

If using phil scopes instead of dictionaries to store the goniometer/detector/beamline/... information, the following function has been added:

.. autofunction:: nexgen.nxs_write.NexusWriter.write_nexus_from_scope


When dealing with an Electron Diffraction dataset, there may also be a need to convert the vectors to mcstas from another coordinate system convention, as well as save the relevant information about the new coordinate system into a NXcoordinate_system_set base class.
The ``ED_call_writers`` function from the ``nxs_write.EDNexusWriter`` takes care of these computations.

.. automodule:: nexgen.nxs_write.EDNexusWriter
    :members:

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

.. automodule:: nexgen.nxs_copy.CopyNexus
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


Identify the scan axes and calculate the scan range
---------------------------------------------------

.. autofunction:: nexgen.nxs_write.NexusWriter.ScanReader


HDF5 metafile reader
--------------------

Metafile definition:

.. automodule:: nexgen.tools.Metafile
    :members:
    :show-inheritance:


When operating a Dectris detector, the goniometer and detector axes values are usually stored in the `config/` dataset.

.. autofunction:: nexgen.tools.MetaReader.update_goniometer

.. autofunction:: nexgen.tools.MetaReader.update_detector_axes


A couple of functions are available for reading the information stored in the metafile and copying it across to the new NeXus file by overwriting the existing values unless otherwise specified:

.. autofunction:: nexgen.tools.MetaReader.overwrite_beam

.. autofunction:: nexgen.tools.MetaReader.overwrite_detector


Reader for Singla detector master file
--------------------------------------

.. autoclass:: nexgen.tools.ED_tools.SinglaMaster
    :members:

.. autofunction:: nexgen.tools.ED_tools.extract_from_SINGLA_master


Logging configuration
=====================

.. automodule:: nexgen.log
    :members:
