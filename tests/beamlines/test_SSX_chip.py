import tempfile

import pytest

from nexgen.beamlines import PumpProbe
from nexgen.beamlines.SSX_chip import (
    Chip,
    compute_goniometer,
    fullchip_blocks_conversion,
    fullchip_conversion_table,
    read_chip_map,
)

test_chip = Chip(
    "testchip",
    num_steps=[20, 20],
    step_size=[0.125, 0.125],
    num_blocks=[2, 2],
    block_size=[3.175, 3.175],
    start_pos=[0.0, 0.0, 0.0],
)

test_goniometer = {"axes": ["omega", "sam_y", "sam_x", "phi"]}


def test_pump_probe():
    pump_probe = PumpProbe()
    pump_probe.pump_status = True
    pump_probe.pump_exposure = 0.01
    assert pump_probe.pump_status is True
    assert pump_probe.pump_exposure == 0.01
    assert pump_probe.pump_delay is None


def test_pump_probe_dict():
    pump_probe = PumpProbe().to_dict()
    assert list(pump_probe.keys()) == [
        "pump_status",
        "pump_exposure",
        "pump_delay",
        "pump_repeat",
    ]
    assert pump_probe["pump_status"] is False


def test_pump_status_set_to_true_if_exposure_is_passed():
    pump_probe = PumpProbe(pump_exposure=0.1)
    assert pump_probe.pump_status is True


def test_chip_tot_blocks():
    assert test_chip.tot_blocks() == 4


def test_chip_windows():
    assert test_chip.tot_windows_per_block() == 400
    assert test_chip.window_size() == (2.5, 2.5)


def test_chip_size():
    size = test_chip.chip_size()
    assert type(size) is tuple
    assert size == (6.35, 6.35)


def test_chip_types():
    assert type(test_chip.num_steps[0]) is int
    assert type(test_chip.step_size[0]) is float
    assert type(test_chip.num_blocks[0]) is int
    assert type(test_chip.block_size[0]) is float


def test_no_chip_map_passed_returns_fullchip():
    res = read_chip_map(None, 1, 1)
    assert type(res) is dict
    assert list(res.values())[0] == "fullchip"


def test_fullchip_conversion_table():
    table = fullchip_conversion_table(test_chip)
    assert len(table) == 4
    assert list(table.keys()) == ["01", "02", "03", "04"]
    assert list(table.values()) == [(0, 0), (0, 1), (1, 1), (1, 0)]


def test_fullchip_blocks_conversion():
    test_pos = {
        (0, 0): 4 * [0.0],
        (0, 1): [0.0, 3.175, 0.0, 0.0],
        (1, 1): [0.0, 5.55, 3.175, 0.0],
        (1, 0): [0.0, 2.375, 3.175, 0.0],
    }
    new_test_pos = fullchip_blocks_conversion(test_pos, test_chip)
    assert list(test_pos.values()) == list(new_test_pos.values())
    assert list(new_test_pos.keys()) == ["01", "02", "03", "04"]


@pytest.fixture
def dummy_chipmap_file():
    lines = [
        "01status    P3011       1\n",
        "02status    P3021       0\n",
        "03status    P3031       0\n",
        "04status    P3041       1\n",
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
    assert list(blocks.keys()) == ["01", "04"]


def test_compute_goniometer_for_full_chip():
    starts = compute_goniometer(test_chip, full=True)
    assert len(starts) == test_chip.tot_blocks()
    assert list(starts.keys()) == [(0, 0), (0, 1), (1, 1), (1, 0)]


def test_compute_goniometer_from_chipmap_for_up_and_down_blocks(dummy_chipmap_file):
    blocks = read_chip_map(
        dummy_chipmap_file.name, test_chip.num_blocks[0], test_chip.num_blocks[1]
    )
    starts = compute_goniometer(test_chip, blocks=blocks)
    assert list(starts.keys()) == ["01", "04"]
    assert starts["01"]["sam_y"] == 0.0
    assert starts["01"]["sam_x"] == 0.0
    assert starts["01"]["direction"] == 1
    assert starts["04"]["sam_y"] == 2.375
    assert starts["04"]["sam_x"] == 3.175
    assert starts["04"]["direction"] == -1
