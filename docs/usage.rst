=====
Usage
=====

**Nexgen** is a Python package that provides a set of tools to write NeXus files for experiments at Diamond Light Source, following
the NXmx application definition for macromolecular crystallography. This is meant to include all relevant experiment metadata
required to process the datasets, including detector and goniometer description.

Installation
------------

Nexgen can be installed using pip.

.. code-block:: console

    pip install nexgen


.. note::
    This project is under development.


Command line tools
------------------

This package started out as an easy way to quickly generate NeXus files from scratch along with blank HDF5 datasets using command line tools.


.. note::
    NOTE ON PARSING

    The command line tools have been refactored as of version ``0.11.0`` and no longer use `freephil <https://freephil.readthedocs.io/en/latest/>`_ 
    because of dependencies issues with some packages being deprecated. Old tools are still available 
    in older nexgen versions.


Getting help
============

Every command line tool in the nexgen package has a help message that explains how to use it and what the options are.
This help message will be printed by using the option `-h`, or `--help`, and each subcommand also has an help message detailing its specific options.

.. code-block:: console

    generate_nexus demo -h



Generating new NeXus files
==========================

 - For an existing dataset

    .. code-block:: console

        generate_nexus 1 File_00_meta.h5 --config config_file.yaml -o /path/to/output/dir -nxs File_01.nxs

 - From scratch, along with blank data (demo)

    .. code-block:: console

        generate_nexus 2 File.nxs -n 3600 --config config_file.yaml --mask /path/to/mask/file


.. note::
    This functionality will only work properly for NXmx datasets.



Generating NXmx-like NeXus files for Electron Diffraction
=========================================================

Example usage for a dataset collected on Dectris Singla 1M detector using a phil parser:

.. code-block:: console

    ED_nexus singla-phil FILE_master.h5 FILE_data_01.h5 FILE_data_02.h5 (etc) --config ED_Singla.yaml 


The instrument name and source are defined by the values parsed from source, which are shown in the following dictionary:

.. code-block:: python

    source = {
        "name": "Diamond Light Source",
        "short_name": "DLS",
        "type": "Electron Source",
        "beamline_name": "eBic",
        "probe": "electron",
    }


.. note::
    As of version `0.6.28`, the source type to go in the NXSource base class has been updated to `Electron Source`.


To specify a more specific name for the `/entry/instrument/name` field, the following command can be added to the command line:

.. code-block:: console

    source.facility_id="DIAMOND MICROSCOPE"

which will result in the instrument name being set to `DIAMOND MICROSCOPE eBic` instead of `DIAMOND eBic`.


The downside of this option is that the external links to the data will now be saved using absolute paths instead of relative.


Example usage for a dataset collected on Dectris Singla 1M detector without the phil parser (new as of version `0.7.3`):

.. code-block:: console

    ED_nexus singla FILE_master.h5 400 -e 0.099 -wl 0.02 -bc 1 1 --axis-name alpha --axis-start 0.0 --axis-inc 0.11


For both CLI tools, in case there is a need to save the NeXus file in a different location than the data files:

.. code-block:: console

    -o /path/to/new/directory



Configuration files
===================

The configuration files passed to the commanf line should be either ``yaml`` or ``json`` files,
implementing the following configuration schema:


.. autopydantic_model:: nexgen.command_line.cli_config.CliConfig
    :model-show-config-summary: True