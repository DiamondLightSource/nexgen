from pathlib import Path

from nexgen.beamlines.i19_2.parameters import CollectionParams


def test_collection_parameters(dummy_eiger_collection_params: CollectionParams):
    dummy_eiger_collection_params.tot_num_images = 10
    assert isinstance(dummy_eiger_collection_params.metafile, Path)
    assert not dummy_eiger_collection_params.axes_pos
    assert not dummy_eiger_collection_params.det_pos
    assert dummy_eiger_collection_params.tot_num_images == 10
