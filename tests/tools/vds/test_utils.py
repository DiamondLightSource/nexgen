from nexgen.tools.vds_tools.utils import find_datasets_in_file


def test_find_datasets_int_file(nexus_file_with_single_dataset):
    nxdata = nexus_file_with_single_dataset["/entry/data"]
    dsets = find_datasets_in_file(nxdata)
    assert len(dsets) == 1
    assert dsets[0] == "data_0001"
