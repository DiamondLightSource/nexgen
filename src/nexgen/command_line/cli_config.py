from typing import Literal

from pydantic import BaseModel, field_validator

from ..nxs_utils import Attenuator, Axis, Beam, DetectorType, Sample, Source
from ..nxs_utils.detector import (
    CetaDetector,
    EigerDetector,
    JungfrauDetector,
    SinglaDetector,
    TristanDetector,
)


class GonioConfig(BaseModel):
    axes: list[Axis]


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
                raise ValueError("Undefined detector type")


class CoordSystemConfig(BaseModel):
    convention: str = "mcstas"
    origin: list[float] | tuple[float, float, float] | None = None
    vectors: list[tuple[float, float, float]] | None = None


class CliConfig(BaseModel):
    gonio: GonioConfig
    instrument: InstrumentConfig
    det: DetectorConfig
    sample: Sample | None = None
    coord: CoordSystemConfig | None = None
