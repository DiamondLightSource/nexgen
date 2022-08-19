===========================
Beamline specific utilities
===========================


Nexgen is currently being used for some specific applications at beamlines I19-2 and I24 at DLS.

Time resolved collections with Tristan 10M detector on I19-2
------------------------------------------------------------

For completeness' sake there is also an option to write a NeXus file for an Eiger detector.
(nexgen was actually born out of a need to write the nxs file for tristan expt)


Serial crystallography
----------------------

I19-2: Tristan and Eiger nexus file writing, SSX with tristan detector.
I24: serial crystallography -> still shots (extruder application), fixed target (TR or not), 3d scan (tbc)



Example usage
*************


Beamlines API
=============

I19-2
-----

TODO. Just a thought. move read_from_xml to either extended request or the GDA tools (in this case maybe rename?) and modify the
I19-2 script with an option that either writes from GDA or does the same as I24 bypassing that completely. 

.. autofunction:: nexgen.beamlines.I19_2_nxs.tristan_writer

.. autofunction:: nexgen.beamlines.I19_2_nxs.eiger_writer

I24
---

TODO. Namedtuple thing

.. autofunction:: nexgen.beamlines.I24_Eiger_nxs.extruder

.. autofunction:: nexgen.beamlines.I24_Eiger_nxs.fixed_target

SSX using Tristan Detector
--------------------------

TODO. Another thought. Considering the idea of having Tristan on I24 this should be usable from both beamlines.
I mean... it should only be a matter of switching the name? I can be easily passed as input argument ...
One thing to remember: different geometries will need to be accounted for when changing this. The goniometer should be mostly fine,
it's all 0s anyway, but I24 does not have a 2theta axis for the detector!

.. autofunction:: nexgen.beamlines.SSX_Tristan_nxs.write_nxs

GDA integration tools
---------------------

Read geometry and detector parameters from GDA-generated JSON files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autofunction:: nexgen.tools.GDAjson2params.read_geometry_from_json

.. autofunction:: nexgen.tools.GDAjson2params.read_detector_params_from_json

Gather beamline and collection information from GDA-generated xml file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: nexgen.tools.ExtendedRequest.ExtendedRequestIO
    :members:
