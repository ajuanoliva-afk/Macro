from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal


Provider = Literal["fred", "eurostat"]
Transform = Literal["level", "yoy", "mom", "change", "qoq_ann"]


@dataclass(frozen=True)
class Observation:
    date: date
    value: float


@dataclass(frozen=True)
class DataSeries:
    key: str
    title: str
    unit: str
    provider: Provider
    observations: tuple[Observation, ...]
    source_id: str
    geo: str | None = None
    vintage: date | None = None
    notes: str = ""

    @property
    def latest(self) -> Observation:
        if not self.observations:
            raise ValueError(f"No hay observaciones para {self.key}")
        return self.observations[-1]


@dataclass(frozen=True)
class FredSpec:
    alias: str
    series_id: str
    title: str
    transform: Transform = "level"
    unit: str = ""
    notes: str = ""


@dataclass(frozen=True)
class EurostatSpec:
    alias: str
    dataset: str
    title: str
    filters: dict[str, str] = field(default_factory=dict)
    unit: str = "%"
    notes: str = ""


@dataclass(frozen=True)
class Alert:
    id: int
    chat_id: int
    provider: Provider
    symbol: str
    geo: str | None
    operator: str
    threshold: float
    last_condition: bool | None
    active: bool

