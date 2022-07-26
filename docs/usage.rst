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
==================

Generating new NeXus files
--------------------------

This package started out as an easy way to quickly generate NeXus files from scratch along with blank HDF5 datasets using command line tools.


**Parsing**
The `freephil <https://freephil.readthedocs.io/en/latest/>`_ package is used for parsing metadata from the command line. 


Getting help
------------

Every command line tool in the nexgen package has a help message that explains how to use it and what the options are.
This help message will be printed by using the option `-h`, or `--help`, and each subcommand also has an help message detailing its specific options.

.. code-block:: console
    copy_nexus --help

.. code-block:: console
    generate_nexus demo -h



Show PHIL parameters
--------------------
In addition to the help message, it is possible to take a look at the list of phil parameters that can/need to be passed to the command line generator.


Creating a new .phil file
-------------------------

Writing the full list of parameters on the command line each time can be time consuming, not to mention subject to typing errors and the like.
For this purpose, it is possible to generate one reusable Phil file containing the beamline description and those values from the experiment 
metadata that can be considered constant.  

Nexgen already includes Phil files for some MX beamlines at Diamond Light Source, which can be viewed and downloaded by running ``nexgen_phil`` with the ``list`` and ``get`` options.
For example, the command

.. code-block:: console
    nexgen_phil list
will return a list of the .phil files currently available, and che chosen file can be downloaded by running:

.. code-block:: console
    nexgen_phil get filename.phil -o  /path/to/directory

In case a .phil file for a specific beamline is not in the list, it is possible to create on using the ``new`` option. While this is a bit more cumbersome, 
it has the advantage of only needing to write most of the parameters once. Once the file is created it can be parsed by ``generate_nexus``, eg.

.. code-block:: console
    generate_nexus 2 -i paramfile.phil output.master_filename=File.nxs 

To access the help message for ``nexgen_phil``:

.. code-block:: console
    nexgen_phil -h


Copying NeXus files
-------------------

How to goes here ...
...
A NeXus file can be copied in full or just parts of it, 

Copy a Nxmx file or a tristan-flavoured file....


DLS beamline specific utilities
===============================

Nexgen is currently being used for some specific applications at beamlines I19-2 and I24 at DLS.

I19-2: Tristan and Eiger nexus file writing, SSX with tristan detector.
I24: serial crystallography -> still shots (extruder application), fixed target (TR or not), 3d scan (tbc)