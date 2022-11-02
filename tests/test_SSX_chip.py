import tempfile

import pytest

from nexgen.beamlines.SSX_chip import Chip, read_chip_map

test_chip = Chip(
    "testchip",
    num_steps=[20, 20],
    step_size=[0.125, 0.125],
    num_blocks=[2, 2],
    block_size=[3.175, 3.175],
    start_pos=[0.0, 0.0, 0.0],
)


def test_no_chip_map_passed_returns_fullchip():
    assert read_chip_map(None, 1, 1) == "fullchip"


@pytest.fixture
def dummy_chipmap_file():
    lines = [
        "01status    P3011       1\n",
        "02status    P3021       1\n",
        "03status    P3031       0\n",
        "04status    P3041       0\n",
    ]
    test_map_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".map", delete=False, encoding="utf-8"
    )
    with test_map_file as map:
        map.writelines(lines)
    yield test_map_file


def test_read_chip_map(dummy_chipmap_file):
    blocks = read_chip_map(
        dummy_chipmap_file.name, test_chip.num_blocks[0], test_chip.num_blocks[1]
    )
    assert type(blocks) == dict and len(blocks) == 2
    assert list(blocks.keys()) == ["01", "02"]
