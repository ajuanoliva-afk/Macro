from __future__ import annotations

import asyncio
from datetime import date
from typing import Any, Iterable

import httpx

from ..models import DataSeries, EurostatSpec, Observation
from ..timeutils import parse_period_date
from .base import DataSourceError


def format_since_time_period(value: date, frequency: str) -> str:
    if frequency == "A":
        return f"{value.year:04d}"
    if frequency == "Q":
        quarter = (value.month - 1) // 3 + 1
        return f"{value.year:04d}-Q{quarter}"
    if frequency == "M":
        return f"{value.year:04d}-{value.month:02d}"
    return value.isoformat()


def decode_jsonstat(payload: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions = payload.get("id")
    sizes = payload.get("size")
    raw_values = payload.get("value", {})
    if not dimensions or not sizes or len(dimensions) != len(sizes):
        errors = payload.get("error")
        raise DataSourceError(f"Respuesta Eurostat no válida: {errors or 'sin dimensiones'}")

    position_codes: list[list[str]] = []
    for dimension_id, size in zip(dimensions, sizes):
        category = payload["dimension"][dimension_id]["category"]
        raw_index = category.get("index", {})
        if isinstance(raw_index, list):
            codes = list(raw_index)
        else:
            codes = [""] * size
            for code, position in raw_index.items():
                if position < size:
                    codes[position] = code
        position_codes.append(codes)

    if isinstance(raw_values, list):
        values = {index: value for index, value in enumerate(raw_values) if value is not None}
    else:
        values = {int(index): value for index, value in raw_values.items()}

    rows: list[dict[str, Any]] = []
    for flat_index, value in values.items():
        remainder = flat_index
        positions = [0] * len(sizes)
        for index in range(len(sizes) - 1, -1, -1):
            positions[index] = remainder % sizes[index]
            remainder //= sizes[index]
        row = {
            dimension_id: position_codes[index][positions[index]]
            for index, dimension_id in enumerate(dimensions)
        }
        row["value"] = float(value)
        rows.append(row)
    return rows


class EurostatClient:
    BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

    def __init__(self, timeout: float = 25.0) -> None:
        self.http = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "MacroTelegramBot/0.1"},
        )

    async def close(self) -> None:
        await self.http.aclose()

    async def _get(
        self,
        dataset: str,
        filters: dict[str, str],
        geos: Iterable[str],
        start: date | None,
    ) -> dict[str, Any]:
        params: list[tuple[str, str]] = [("lang", "en")]
        params.extend(filters.items())
        params.extend(("geo", geo) for geo in geos)
        if start:
            params.append(
                (
                    "sinceTimePeriod",
                    format_since_time_period(start, filters.get("freq", "")),
                )
            )

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self.http.get(
                    f"{self.BASE_URL}/{dataset}", params=params
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("error"):
                    raise DataSourceError(str(payload["error"]))
                return payload
            except (httpx.HTTPError, ValueError, DataSourceError) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2**attempt))
        raise DataSourceError(f"Eurostat no respondió correctamente: {last_error}")

    async def fetch(
        self,
        spec: EurostatSpec,
        geos: Iterable[str],
        start: date | None = None,
    ) -> list[DataSeries]:
        requested_geos = tuple(dict.fromkeys(geos))
        payload = await self._get(spec.dataset, spec.filters, requested_geos, start)
        rows = decode_jsonstat(payload)

        result: list[DataSeries] = []
        for geo in requested_geos:
            observations = sorted(
                (
                    Observation(parse_period_date(row["time"]), row["value"])
                    for row in rows
                    if row.get("geo") == geo and row.get("time")
                ),
                key=lambda item: item.date,
            )
            if observations:
                result.append(
                    DataSeries(
                        key=spec.alias,
                        title=spec.title,
                        unit=spec.unit,
                        provider="eurostat",
                        observations=tuple(observations),
                        source_id=spec.dataset,
                        geo=geo,
                        notes=spec.notes,
                    )
                )
        if not result:
            raise DataSourceError(
                f"Eurostat no devolvió datos de {spec.alias} para "
                + ", ".join(requested_geos)
            )
        return result
