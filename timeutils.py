from __future__ import annotations

import re
from calendar import monthrange
from datetime import date


PERIOD_RE = re.compile(r"^(1m|3m|6m|1y|2y|5y|10y|20y|max)$", re.I)


def is_period(value: str) -> bool:
    return bool(PERIOD_RE.match(value.strip()))


def months_ago(reference: date, months: int) -> date:
    absolute = reference.year * 12 + reference.month - 1 - months
    year, month_zero = divmod(absolute, 12)
    month = month_zero + 1
    return date(year, month, min(reference.day, monthrange(year, month)[1]))


def period_start(period: str, reference: date | None = None) -> date | None:
    reference = reference or date.today()
    period = period.lower()
    if period == "max":
        return None
    number = int(period[:-1])
    suffix = period[-1]
    months = number if suffix == "m" else number * 12
    return months_ago(reference, months)


def parse_period_date(value: str) -> date:
    if "-Q" in value:
        year, quarter = value.split("-Q")
        return date(int(year), (int(quarter) - 1) * 3 + 1, 1)
    if len(value) == 4:
        return date(int(value), 1, 1)
    if len(value) == 7:
        return date.fromisoformat(value + "-01")
    return date.fromisoformat(value[:10])

