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


**Parsing**
The `freephil <https://freephil.readthedocs.io/en/latest/>`_ package is used for parsing metadata from the command line.


Getting help
============

Every command line tool in the nexgen package has a help message that explains how to use it and what the options are.
This help message will be printed by using the option `-h`, or `--help`, and each subcommand also has an help message detailing its specific options.

.. code-block:: console

    copy_nexus --help

.. code-block:: console

    generate_nexus demo -h



Show PHIL parameters
====================
In addition to the help message, it is possible to take a look at the list of phil parameters that can/need to be passed to the command line generator.

.. code-block:: console

    generate_nexus 3 -c

It is also possible to view more details about the Phil parameters and definition attributes by setting the `attributes_level` parameter with the `-a` argument.
Th default value is set to 0, which will only show names and default values of the parameters.

.. code-block:: console

    generate_nexus 1 -c -a 2


Creating a new .phil file
=========================

Writing the full list of parameters on the command line each time can be time consuming, not to mention subject to typing errors and the like.
For this purpose, it is possible to generate one reusable Phil file containing the beamline description and those values from the experiment
metadata that can be considered constant.

Nexgen already includes Phil files for some MX beamlines at Diamond Light Source, which can be viewed and downloaded by running ``nexgen_phil`` with the ``list`` and ``get`` options.
For example, the command

.. code-block:: console

    nexgen_phil list

will return a list of the .phil files currently available, and che chosen file can be downloaded by running:

.. code-block:: console

    nexgen_phil get paramfile.phil -o  /path/to/directory

In case a .phil file for a specific beamline is not in the list, it is possible to either download a blank template (also listed) to fill in manually or create on using the ``new`` option. While this is a bit more cumbersome,
it has the advantage of only needing to write most of the parameters once. Once the file is created it can be parsed by ``generate_nexus``, eg.

.. code-block:: console

    generate_nexus 2 -i paramfile.phil output.master_filename=File.nxs input.vds_writer=dataset

To access the help message for ``nexgen_phil``:

.. code-block:: console

    nexgen_phil -h

Generating new NeXus files
==========================

 - For an existing dataset

    .. code-block:: console

        generate_nexus 1 beamline.phil input.datafile=File_00*.h5 input.snaked=True \
        goniometer.starts=0,0,0,0 goniometer.ends=0,0,1,2 goniometer.increments=0,0,0.1,0.2  \
        detector.exposure_time=0.095 detector.beam_center=989.8,1419 detector.overload=65535 \
        detector.starts=0,140 detector.ends=0,140 beam.wavelength=0.4859

 - From scratch, along with blank data (demo)

    .. code-block:: console

        generate_nexus 2 -i/-e beamline.phil output.master_filename=File.nxs input.vds_writer=dataset (etc...)

 - For an existing dataset which also has a meta.h5 file

    .. code-block:: console

        generate_nexus 3 beamline.phil input.metafile=File_meta.h5 input.vds_writer=dataset output.master_filename=/path/to/File.nxs


.. note::
    This functionality will only work properly for Eiger and Tristan detectors.



Generating NXmx-like NeXus files for Electron Diffraction
=========================================================

Example usage for a dataset collected on Dectris Singla 1M detector using a phil parser:

.. code-block:: console

    ED_nexus singla-phil ED_Singla.phil input.datafiles=FILE_data_*.h5 goniometer.starts=0,0,0,0 \
    goniometer.ends=900,0,0,0 goniometer.increments=1,0,0,0 detector.starts=400 detector.beam_center=1,1 \
    -m FILE_master.h5

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


Copying NeXus files
===================

 - Copy a nexus file in full, or just parts of it. T

    This tool will create a new file File_copy.nxs, in order to avoid modifying the orifinal data, with just the requested metadata.

    .. code-block:: console

        copy_nexus gen input.original_nexus=File.nxs input.simple_copy=True

    .. code-block:: console

        copy_nexus gen original_nexus=File.nxs data_filename=File_0001.h5 skip=NXdata skip=NXsample

 - Copy metadata from a Tristan NeXus file to NXmx format.

    The main application fo this tool is to copy the necessary metadata to a new NeXus file following the NXmx format after binning event data into images.
    The default `experiment_type` for copying Tristan metadata is set to rotation; when dealing with a single image, this value can be set to stationary like in the example below.

    .. code-block:: console

        copy_nexus tristan tristan_nexus=Tristan_img.nxs data_filename=Tristan_img_0001.h5 experiment_type=stationary
