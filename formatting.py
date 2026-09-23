from __future__ import annotations

from datetime import date

from .catalog import GEO_LABELS
from .models import DataSeries


def format_number(value: float) -> str:
    absolute = abs(value)
    if absolute >= 1000:
        return f"{value:,.1f}"
    if absolute >= 100:
        return f"{value:.1f}"
    return f"{value:.2f}"


def format_date(value: date) -> str:
    return value.isoformat()


def one_line(series: DataSeries) -> str:
    latest = series.latest
    previous = series.observations[-2] if len(series.observations) > 1 else None
    delta = ""
    if previous:
        change = latest.value - previous.value
        delta = f" ({change:+.2f})"
    geo = f" · {GEO_LABELS.get(series.geo, series.geo)}" if series.geo else ""
    return (
        f"{series.title}{geo}: {format_number(latest.value)} {series.unit}"
        f"{delta} · {format_date(latest.date)}"
    )


def series_summary(series: DataSeries, rows: int = 8) -> str:
    geo = f" · {GEO_LABELS.get(series.geo, series.geo)}" if series.geo else ""
    vintage = f" · vintage {series.vintage.isoformat()}" if series.vintage else ""
    lines = [
        f"{series.title}{geo}",
        f"{series.source_id} · {series.unit}{vintage}",
        "",
    ]
    for item in series.observations[-rows:][::-1]:
        lines.append(f"{format_date(item.date)}  {format_number(item.value)}")
    if series.notes:
        lines.extend(["", series.notes])
    return "\n".join(lines)

