from nexgen.beamlines.SSX_chip import (
    Chip,
    compute_goniometer,
    fullchip_blocks_conversion,
    fullchip_conversion_table,
    read_chip_map,
)

test_chip = Chip(
    "testchip",
    num_steps=(20, 20),
    step_size=(0.125, 0.125),
    num_blocks=(2, 2),
    block_size=(3.175, 3.175),
    start_pos=(0.0, 0.0, 0.0),
)

test_goniometer = {"axes": ["omega", "sam_y", "sam_x", "phi"]}


def test_chip_tot_blocks():
    assert test_chip.tot_blocks() == 4


def test_chip_windows():
    assert test_chip.tot_windows_per_block() == 400
    assert test_chip.window_size() == (2.5, 2.5)


def test_chip_size():
    size = test_chip.chip_size()
    assert isinstance(size, tuple)
    assert size == (6.35, 6.35)


def test_chip_types():
    assert isinstance(test_chip.num_steps[0], int)
    assert isinstance(test_chip.step_size[0], float)
    assert isinstance(test_chip.num_blocks[0], int)
    assert isinstance(test_chip.block_size[0], float)


def test_no_chip_map_passed_returns_fullchip():
    res = read_chip_map(None, 1, 1)
    assert isinstance(res, dict)
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


def test_read_chip_map(dummy_chipmap):
    blocks = read_chip_map(
        dummy_chipmap, test_chip.num_blocks[0], test_chip.num_blocks[1]
    )
    assert isinstance(blocks, dict) and len(blocks) == 2
    assert list(blocks.keys()) == ["01", "04"]


def test_compute_goniometer_for_full_chip():
    starts = compute_goniometer(test_chip, full=True)
    assert len(starts) == test_chip.tot_blocks()
    assert list(starts.keys()) == [(0, 0), (0, 1), (1, 1), (1, 0)]


def test_compute_goniometer_from_chipmap_for_up_and_down_blocks(dummy_chipmap):
    blocks = read_chip_map(
        dummy_chipmap, test_chip.num_blocks[0], test_chip.num_blocks[1]
    )
    starts = compute_goniometer(test_chip, blocks=blocks)
    assert list(starts.keys()) == ["01", "04"]
    assert starts["01"]["sam_y"] == 0.0
    assert starts["01"]["sam_x"] == 0.0
    assert starts["01"]["direction"] == 1
    assert starts["04"]["sam_y"] == 2.375
    assert starts["04"]["sam_x"] == 3.175
    assert starts["04"]["direction"] == -1
