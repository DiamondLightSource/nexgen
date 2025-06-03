from pathlib import Path

import pytest

from nexgen.command_line.cli_config import CliConfig, DetectorConfig
from nexgen.nxs_utils import EigerDetector, TristanDetector


@pytest.fixture
def examples_root() -> Path:
    return Path(__file__).absolute().parent


def test_load_config_from_yaml(examples_root: Path):
    config = CliConfig.from_file(examples_root / "example_yaml.yaml")

    assert len(config.gonio.axes) == 3
    assert config.gonio.scan_type == "grid"
    assert not config.gonio.scan_axis

    assert len(config.instrument.beam.wavelength) == 2
    assert not config.instrument.beam.flux
    assert config.instrument.source.beamline == "ixx"
    assert not config.instrument.attenuator.transmission

    assert isinstance(config.det.params, EigerDetector)
    assert len(config.det.axes) == 1
    assert config.det.axes[0].name == "det_z"
    assert config.det.axes[0].start_pos == 1350


def test_load_config_from_json(examples_root: Path):
    config = CliConfig.from_file(examples_root / "example_json.json")

    assert len(config.gonio.axes) == 2
    assert config.gonio.scan_type == "rotation"
    assert config.gonio.scan_axis == "phi"

    assert config.instrument.beam.wavelength == 0.6
    assert config.instrument.source.beamline == "i19-2"
    assert config.instrument.attenuator.transmission == 0.2

    assert isinstance(config.det.params, TristanDetector)
    assert len(config.det.axes) == 2
    assert config.det.axes[0].name == "two_theta" and config.det.axes[1].name == "det_z"
    assert config.det.axes[0].start_pos == 90.0
    assert config.det.axes[1].start_pos == 250.0


def test_config_raises_error_for_unknown_detector(examples_root: Path):
    new_det = {
        "axes": [
            {
                "name": "det_z",
                "depends": ".",
                "transformation_type": "translation",
                "vector": (0, 0, 1),
                "start_pos": 250.0,
            }
        ],
        "params": {
            "description": "NewDetector",
            "image_size": [1000, 2000],
        },
        "mode": "events",
        "exposure_time": 100,
        "beam_center": [150, 203],
        "module": {
            "fast_axis": (1, 0, 0),
            "slow_axiz": (0, -1, 0),
        },
    }
    with pytest.raises(ValueError):
        DetectorConfig(**new_det)


def test_cli_config_fails_to_load_wrong_file_extension():
    test_txt_file = Path("config.txt")
    with pytest.raises(IOError):
        CliConfig.from_file(test_txt_file)
