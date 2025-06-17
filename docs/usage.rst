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


The instrument name and source are defined by the values parsed from source, which can be defined in the config file as follows:

.. code-block:: yaml

    instrument:
        source:
            beamline: "eBIC"
            facility:
                name: "Diamond Light Source"
                short_name: "DLS"
                type: "Electron Source"
                id: "DIAMOND MICROSCOPE"
            probe: "electron"


Passing a facility id allows the user to specify a more specific name for the `/entry/instrument/name` field; 
this will result in the instrument name being set to `DIAMOND MICROSCOPE eBic` instead of `DIAMOND eBic`.


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
implementing the configuration schema described in :ref:`cli-config-section`.


Example yaml
************

.. code-block:: yaml

    gonio:
        axes:
            - name: phi
            depends: "."
            transformation_type: rotation
            vector: [-1,0,0]
            start_pos: 10.0
            - name: sam_z
            depends: "phi"
            transformation_type: translation
            vector: [0,0,1]
            start_pos: 0.0
            increment: 0.125
            num_steps: 20
            - name: sam_x
            depends: "sam_z"
            transformation_type: translation
            vector: [1,0,0]
            start_pos: 0.0
            increment: 0.125
            num_steps: 20
        scan_type: "grid"
        snaked_scan: True

    instrument:
        beam:
            wavelength: [0.4, 0.6]
            wavelength_weights: [0.1, 0.2]
            flux: null
        attenuator:
            transmission: null
        source:
            beamline: "ixx"

    det:
        axes:
            - name: det_z
            depends: "."
            transformation_type: translation
            vector: [0,0,1]
            start_pos: 1350
        params:
            description: Eiger2 X 9M
            image_size: [3262, 3108]
            sensor_material: CdTe
            overload: 65535
            underload: -1
        beam_center: [1134, 1458]
        exposure_time: 0.01
        module:
            fast_axis: [-1,0,0]
            slow_axis: [0,1,0]

