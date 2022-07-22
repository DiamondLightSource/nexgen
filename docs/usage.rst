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
uses `freephil <https://freephil.readthedocs.io/en/latest/>`_ for parsing metadata 
HOW-TO goes here

Getting help
------------

Every command line tool in the nexgen package has a help message that explains how to use it and what the options are.
This help message will be printed by using the option `-h`, or `--help`.

For example,

.. code-block:: console
    generate_nexus -h

.. code-block:: console
    copy_nexus --help

will show ...
Each subcommand also has an help message detailing its specific options.




Show PHIL parameters
--------------------
In addition to the help message, it is possible to take a look at the list of phil parameters that can/need to be passed to the command line generator.

NB. TODO FIXME -c/-a options are broken with subcommands... especially they seem to be for generate_nexus 2
generate_nexus -c -a 2 3 does exactly what it's supposed to!

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

For more information, ``nexgen_phil`` also has an help message.
.. code-block:: console
    nexgen_phil -h


TODO. Maybe add a downloadable template??? It's not a big step from what I have. 
      Something like nexus_phil get template -n name.phil (beamline template different from cli template, could also include snaked, vds etc if cli)

Copying NeXus files
-------------------

How to goes here ...
...
A NeXus file can be copied in full or just parts of it, 

Copy a Nxmx file or a tristan-flavoured file....


DLS beamline specific Utilities
===============================

I19-2 & I24 stuff goes here ...

TODO. It would be nice to have a decent command line tool that uses them. (also for simulation!) 

A couple of small utilities for specific applications at beamlines I19-2 and I24 

I19-2: Tristan and Eiger nexus file writing, SSX with tristan detector.
I24: serial crystallography -> still shots (extruder application), fixed target (TR or not), 3d scan (tbc)