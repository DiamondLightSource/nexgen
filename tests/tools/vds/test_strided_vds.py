from unittest.mock import MagicMock, patch

import numpy as np

from nexgen.tools.vds_tools.strided_mapping import (
    SingleDataset,
    create_dataset_list,
    create_vds_layout,
    write_strided_vds,
)


def test_create_dataset_list(nexus_file_with_multiple_datasets):
    # with tempfile.NamedTemporaryFile(suffix=".nxs", delete=True)
    with patch("nexgen.tools.vds_tools.strided_mapping.h5py.Dataset") as patch_dset:
        patch_dset.return_value.__enter__.return_value = MagicMock()
        patch_dset.return_value.__enter__.return_value.shape = (10, 2, 3)
        dsets = create_dataset_list(
            nexus_file_with_multiple_datasets["/entry/data"], start_index=0
        )

        assert len(dsets) == 2
        assert dsets[0].name == "data_0001"
        assert dsets[1].name == "data_0002"

        for dset in dsets:
            assert dset.start_index == 0
            assert dset.stride == 2


def test_create_vds_layout():
    dset_list = [
        SingleDataset(name="data_01", src_shape=(6, 2, 2), start_index=1, stride=2)
    ]
    expected_shape = (3, 2, 2)

    layout = create_vds_layout(dset_list, expected_shape, np.uint16)

    assert layout.shape == expected_shape
    assert list(layout._src_filenames)[0] == b"."


@patch("nexgen.tools.vds_tools.strided_mapping.create_dataset_list")
@patch("nexgen.tools.vds_tools.strided_mapping.create_vds_layout")
def test_write_strided_vds(mock_dset_list, mock_layout, nexus_file_with_single_dataset):
    with patch(
        "nexgen.tools.vds_tools.strided_mapping.h5py.Group.create_virtual_dataset"
    ) as mock_create:
        write_strided_vds(nexus_file_with_single_dataset, (10, 2, 3), 0)

        mock_dset_list.assert_called_once()
        mock_layout.assert_called_once()
        mock_create.assert_called_once()
