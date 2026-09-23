from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import httpx

from ..models import DataSeries, FredSpec, Observation
from ..timeutils import months_ago
from ..transforms import transform_observations, trim_from
from .base import DataSourceError


class FredClient:
    BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(self, api_key: str, timeout: float = 25.0) -> None:
        self.api_key = api_key
        self.http = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "MacroTelegramBot/0.1"},
        )

    async def close(self) -> None:
        await self.http.aclose()

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = {"api_key": self.api_key, "file_type": "json", **params}
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self.http.get(
                    f"{self.BASE_URL}/{path}", params=query
                )
                response.raise_for_status()
                payload = response.json()
                if "error_message" in payload:
                    raise DataSourceError(payload["error_message"])
                return payload
            except (httpx.HTTPError, ValueError, DataSourceError) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2**attempt))
        raise DataSourceError(f"FRED no respondió correctamente: {last_error}")

    async def series_info(self, series_id: str) -> dict[str, Any]:
        payload = await self._get("series", {"series_id": series_id})
        series = payload.get("seriess", [])
        if not series:
            raise DataSourceError(f"FRED no reconoce la serie {series_id}")
        return series[0]

    async def fetch(
        self,
        spec: FredSpec,
        start: date | None = None,
        vintage: date | None = None,
    ) -> DataSeries:
        fetch_start = start
        if start and spec.transform == "yoy":
            fetch_start = months_ago(start, 13)
        elif start and spec.transform in {"mom", "change", "qoq_ann"}:
            fetch_start = start - timedelta(days=400 if spec.transform == "qoq_ann" else 45)

        params: dict[str, Any] = {
            "series_id": spec.series_id,
            "sort_order": "asc",
        }
        if fetch_start:
            params["observation_start"] = fetch_start.isoformat()
        if vintage:
            params["realtime_start"] = vintage.isoformat()
            params["realtime_end"] = vintage.isoformat()
            params["observation_end"] = vintage.isoformat()

        info_task = self.series_info(spec.series_id)
        values_task = self._get("series/observations", params)
        info, payload = await asyncio.gather(info_task, values_task)

        observations: list[Observation] = []
        for item in payload.get("observations", []):
            raw = item.get("value")
            if raw in (None, ".", ""):
                continue
            try:
                observations.append(
                    Observation(date.fromisoformat(item["date"]), float(raw))
                )
            except (KeyError, TypeError, ValueError):
                continue
        if not observations:
            raise DataSourceError(
                f"FRED no devolvió datos para {spec.series_id}. "
                "Puede ser una serie no disponible o sin licencia vigente."
            )

        transformed = transform_observations(observations, spec.transform)
        transformed = trim_from(transformed, start)
        if not transformed:
            raise DataSourceError(
                f"No hay suficientes observaciones para calcular {spec.title}"
            )

        title = spec.title if spec.title != spec.series_id else info.get("title", spec.title)
        unit = spec.unit or info.get("units", "")
        return DataSeries(
            key=spec.alias,
            title=title,
            unit=unit,
            provider="fred",
            observations=transformed,
            source_id=spec.series_id,
            vintage=vintage,
            notes=spec.notes,
        )

    async def search(self, text: str, limit: int = 8) -> list[dict[str, Any]]:
        payload = await self._get(
            "series/search",
            {
                "search_text": text,
                "limit": min(max(limit, 1), 20),
                "order_by": "popularity",
                "sort_order": "desc",
            },
        )
        return payload.get("seriess", [])
