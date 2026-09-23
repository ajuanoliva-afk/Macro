from __future__ import annotations

from datetime import date

from .models import Observation, Transform


def _one_year_ago(value: date) -> date:
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def transform_observations(
    observations: tuple[Observation, ...] | list[Observation],
    transform: Transform,
) -> tuple[Observation, ...]:
    ordered = sorted(observations, key=lambda item: item.date)
    if transform == "level":
        return tuple(ordered)

    output: list[Observation] = []
    if transform == "yoy":
        values = {item.date: item.value for item in ordered}
        for item in ordered:
            previous = values.get(_one_year_ago(item.date))
            if previous not in (None, 0):
                output.append(
                    Observation(item.date, (item.value / previous - 1.0) * 100.0)
                )
        return tuple(output)

    for previous, current in zip(ordered, ordered[1:]):
        if transform == "change":
            value = current.value - previous.value
        elif previous.value == 0:
            continue
        elif transform == "mom":
            value = (current.value / previous.value - 1.0) * 100.0
        elif transform == "qoq_ann":
            value = ((current.value / previous.value) ** 4 - 1.0) * 100.0
        else:
            raise ValueError(f"Transformación no soportada: {transform}")
        output.append(Observation(current.date, value))
    return tuple(output)


def trim_from(
    observations: tuple[Observation, ...], start: date | None
) -> tuple[Observation, ...]:
    if start is None:
        return observations
    return tuple(item for item in observations if item.date >= start)

