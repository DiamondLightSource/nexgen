from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator  # , ValidationError

from ..nxs_utils import Attenuator, Axis, Beam, DetectorType, Sample, Source
from ..nxs_utils.detector import (
    CetaDetector,
    EigerDetector,
    JungfrauDetector,
    SinglaDetector,
    TristanDetector,
)
from ..utils import coerce_to_path

JSON_EXT = ".json"
YAML_EXT = ".yaml"


class GonioConfig(BaseModel):
    axes: list[Axis]
    scan_axis: str | None = None  # only really needed for events
    scan_type: Literal["rotation", "grid"] = "rotation"
    snaked_scan: bool = False


class InstrumentConfig(BaseModel):
    source: Source
    beam: Beam
    attenuator: Attenuator


class ModuleConfig(BaseModel):
    fast_axis: list[float] | tuple[float, float, float]
    slow_axis: list[float] | tuple[float, float, float]


class DetectorConfig(BaseModel):
    axes: list[Axis]
    params: DetectorType
    beam_center: list[float] | tuple[float, float]
    exposure_time: float
    module: ModuleConfig
    mode: Literal["images", "events"] = "images"

    @field_validator("params", mode="before")
    @classmethod
    def _parse_params(cls, params: dict | DetectorType):
        if isinstance(params, DetectorType):
            return params
        else:
            if "eiger" in params["description"].lower():
                return EigerDetector(**params)
            elif "tristan" in params["description"].lower():
                return TristanDetector(**params)
            elif "jungfrau" in params["description"].lower():
                return JungfrauDetector(**params)
            elif "singla" in params["description"].lower():
                return SinglaDetector(**params)
            elif "ceta" in params["description"].lower():
                return CetaDetector(**params)
            else:
                raise ValueError("Unknown detector type")


class CoordSystemConfig(BaseModel):
    convention: str = "mcstas"
    origin: list[float] | tuple[float, float, float] | None = None
    vectors: list[tuple[float, float, float]] | None = None


class CliConfig(BaseModel):
    """General configuration model for command line tools."""

    gonio: GonioConfig
    instrument: InstrumentConfig
    det: DetectorConfig
    sample: Sample | None = None
    coord_system: CoordSystemConfig | None = None

    @classmethod
    def from_file(cls, filename: str | Path):
        config_file = coerce_to_path(filename)
        if config_file.suffix == JSON_EXT:
            _raw_params = config_file.read_text()
            config = cls.model_validate_json(_raw_params)
        elif config_file.suffix == YAML_EXT:
            with open(config_file) as fh:
                _raw_params = yaml.load(fh, yaml.Loader)
            config = cls(**_raw_params)
        else:
            raise IOError("Please pass a valid json or yaml file.")
        return config
