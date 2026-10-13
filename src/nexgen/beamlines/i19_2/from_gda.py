"""A writer to be used from GDA, usually only called from a command
line tool or a REST call.
"""

from nexgen.beamlines.i19_2.parameters import ParamsFromGDA


def _get_metadata_from_ecr():
    pass


# TODO decide what to do about geometry_json and detector_json
# They should not even be needed as those values are pretty fixed now
def gda_nexus_writer(parameters: ParamsFromGDA):
    # Get metadata from ecr
    # Build CollectionParameters, including axes_pos and det_pos
    # Get master file name
    # Work out additional parameters for eiger
    pass
