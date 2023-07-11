===
API
===

.. automodule:: nexgen
    :members:
    :show-inheritance:


Defining the various parts of a nexus file
==========================================

.. automodule:: nexgen.nxs_utils
    :members:
    :show-inheritance:
    :inherited-members:
    :imported-members:

Axes
----

.. automodule:: nexgen.nxs_utils.Axes


.. autoclass:: nexgen.nxs_utils.TransformationType
    :members:
    :imported-members:


.. autoclass:: nexgen.nxs_utils.Axis
    :members:
    :imported-members:


Scans
-----

.. automodule:: nexgen.nxs_utils.ScanUtils
    :members:
    :show-inheritance:


Goniometer
----------

.. automodule:: nexgen.nxs_utils.Goniometer
    :members:
    :imported-members:


Detector
--------

.. automodule:: nexgen.nxs_utils.Detector
    :members:
    :inherited-members:
    :show-inheritance:
    :imported-members:


Source
------

.. automodule:: nexgen.nxs_utils.Source
    :members:
    :imported-members:


Sample
------

.. automodule:: nexgen.nxs_utils.Sample
    :members:
    :imported-members:



Writing tools
=============

NXmx writers
------------

For a standard NXmx data collection

.. autoclass:: nexgen.nxs_write.NXmxWriter.NXmxFileWriter
    :members:
    :show-inheritance:


For an event-mode data collection using a Tristan detector

.. autoclass:: nexgen.nxs_write.NXmxWriter.EventNXmxFileWriter
    :members:
    :inherited-members:


For an Electron Diffraction collection using NXmx-like format nexus files

.. autoclass:: nexgen.nxs_write.NXmxWriter.EDNXmxFileWriter
    :members:
    :inherited-members:



NXclass writers
---------------

All the NXclass writers available can be found in:

.. automodule:: nexgen.nxs_write.NXclassWriters
    :members:


Old tools
---------

.. note:: The following tools will soon be deprecated.

Older tools can stiil be used with the same functionality. The NXclass writers can be called using the ``call_writers`` function,
with the exception of ``write_NXentry``, ``write_NXdatetime`` and ``write_NXnote``.

.. autofunction:: nexgen.command_line.cli_utils.call_writers


To identify the scan axes and calculate the scan range:

.. autofunction:: nexgen.command_line.cli_utils.ScanReader


When dealing with an Electron Diffraction dataset, there may also be a need to convert the vectors to mcstas from another coordinate system convention,
as well as save the relevant information about the new coordinate system into a NXcoordinate_system_set base class.
The ``ED_call_writers`` function from the ``nxs_write.EDNexusWriter`` takes care of these computations.

.. automodule:: nexgen.nxs_write.EDNexusWriter
    :members:


Finally, if using phil scopes instead of dictionaries to store the goniometer/detector/beamline/... information, the following function has been added:

.. autofunction:: nexgen.command_line.cli_utils.write_nexus_from_scope


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


HDF5 metafile reader
--------------------

Metafile definition:

.. automodule:: nexgen.tools.Metafile
    :members:
    :show-inheritance:


When operating a Dectris detector, the goniometer and detector axes values are usually stored in the `config/` dataset.

.. autofunction:: nexgen.tools.MetaReader.update_axes_from_meta


If there's a need to write a VDS dataset from data collected on a Dectris detector, it might be useful to first find out the
data type using the information stored in the `meta` file.

.. autofunction:: nexgen.tools.MetaReader.define_vds_data_type


Reader for Singla detector master file
--------------------------------------

.. autoclass:: nexgen.tools.ED_tools.SinglaMaster
    :members:

.. autofunction:: nexgen.tools.ED_tools.extract_from_SINGLA_master

Tools to calculate the beam center of an Electron Diffraction experiment:

.. autofunction:: nexgen.tools.ED_tools.centroid_max

.. autofunction:: nexgen.tools.ED_tools.find_beam_centre


Logging configuration
=====================

.. automodule:: nexgen.log
    :members:
