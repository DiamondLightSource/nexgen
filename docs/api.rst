===
API
===

Defining the various parts of a nexus file
==========================================

.. autoclass:: nexgen.utils.Point3D


Axes
----

.. automodule:: nexgen.nxs_utils.axes
    :members:
    :show-inheritance:


Scans
-----

.. automodule:: nexgen.nxs_utils.scan_utils
    :members: identify_osc_axis, identify_grid_scan_axes, calculate_scan_points


.. autoclass:: nexgen.nxs_utils.scan_utils.GridScanOptions
    :members:


.. autoexception:: nexgen.nxs_utils.scan_utils.ScanAxisNotFoundError


.. autoexception:: nexgen.nxs_utils.scan_utils.ScanAxisError


Goniometer
----------

.. automodule:: nexgen.nxs_utils.goniometer
    :members:


Detector
--------

.. automodule:: nexgen.nxs_utils.detector
    :members:
    :inherited-members:
    :show-inheritance:


Source
------

.. automodule:: nexgen.nxs_utils.source
    :members:
    :show-inheritance:


Sample
------

.. automodule:: nexgen.nxs_utils.sample
    :members:
    :show-inheritance:



Writing tools
=============

NXmx writers
------------

For a standard NXmx data collection

.. autoclass:: nexgen.nxs_write.nxmx_writer.NXmxFileWriter
    :members:
    :show-inheritance:


For an event-mode data collection using a Tristan detector

.. autoclass:: nexgen.nxs_write.nxmx_writer.EventNXmxFileWriter
    :members:
    :show-inheritance:
    :inherited-members:


For an Electron Diffraction collection using NXmx-like format nexus files.
When dealing with an Electron Diffraction dataset, there may also be a need to convert the vectors to mcstas from another coordinate system convention,
as well as save the relevant information about the new coordinate system into a NXcoordinate_system_set base class. This writer takes care of these issues.

.. autoclass:: nexgen.nxs_write.ed_nxmx_writer.EDNXmxFileWriter
    :members:
    :show-inheritance:



NXclass writers
---------------

All the NXclass writers available can be found in:

.. automodule:: nexgen.nxs_write.nxclass_writers
    :members:



Writing blank datasets
----------------------

Generating blank images
^^^^^^^^^^^^^^^^^^^^^^^

Using an *Eiger* or *Tristan* detector mask ...

.. autofunction:: nexgen.tools.data_writer.build_an_eiger

.. autofunction:: nexgen.tools.data_writer.build_a_tristan



.. autofunction:: nexgen.tools.data_writer.generate_image_files


Generating pseudo-events
^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: nexgen.tools.data_writer.pseudo_event_list



.. autofunction:: nexgen.tools.data_writer.generate_event_files


VDS writer
----------

.. automodule:: nexgen.tools.vds_tools
    :members:


Copying tools
=============

.. automodule:: nexgen.nxs_copy.copy_nexus
    :members:

.. automodule:: nexgen.nxs_copy.copy_tristan_nexus
    :members:



Utilities
=========

.. automodule:: nexgen.utils
    :members:


**Writing tools**

.. automodule:: nexgen.nxs_write.write_utils
    :members:

**Copying tools**

.. automodule:: nexgen.nxs_copy.copy_utils
    :members:


HDF5 metafile reader
--------------------

Metafile definition:

.. automodule:: nexgen.tools.metafile
    :members:
    :show-inheritance:


When operating a Dectris detector, the goniometer and detector axes values are usually stored in the `config/` dataset.

.. autofunction:: nexgen.tools.meta_reader.update_axes_from_meta


If there's a need to write a VDS dataset from data collected on a Dectris detector, it might be useful to first find out the
data type using the information stored in the `meta` file.

.. autofunction:: nexgen.tools.meta_reader.define_vds_data_type


Reader for Singla detector master file
--------------------------------------

.. autoclass:: nexgen.tools.ed_tools.SinglaMaster
    :members:

.. autofunction:: nexgen.tools.ed_tools.extract_exposure_time_from_master

.. autofunction:: nexgen.tools.ed_tools.extract_start_time_from_master

.. autofunction:: nexgen.tools.ed_tools.extract_detector_info_from_master


Tools to calculate the beam center of an Electron Diffraction experiment:

.. autofunction:: nexgen.tools.ed_tools.centroid_max

.. autofunction:: nexgen.tools.ed_tools.find_beam_centre


Logging configuration
=====================

.. automodule:: nexgen.log
    :members:



.. _cli-config-section:

CLI configuration
=================


.. autopydantic_model:: nexgen.command_line.cli_config.CliConfig
    :inherited-members: BaseModel
    :model-show-config-summary: True


.. autopydantic_model:: nexgen.command_line.cli_config.GonioConfig
    :model-show-config-summary: False


.. autopydantic_model:: nexgen.command_line.cli_config.InstrumentConfig
    :model-show-config-summary: False


.. autopydantic_model:: nexgen.command_line.cli_config.DetectorConfig
    :model-show-config-summary: False


.. autopydantic_model:: nexgen.command_line.cli_config.ModuleConfig
    :model-show-config-summary: False


.. autopydantic_model:: nexgen.command_line.cli_config.CoordSystemConfig
    :model-show-config-summary: False
