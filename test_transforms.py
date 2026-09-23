from datetime import date

import pytest

from macrobot.models import Observation
from macrobot.transforms import transform_observations


def test_yoy_uses_same_month_previous_year():
    observations = (
        Observation(date(2024, 1, 1), 100),
        Observation(date(2025, 1, 1), 105),
    )
    result = transform_observations(observations, "yoy")
    assert result[0].date == date(2025, 1, 1)
    assert result[0].value == pytest.approx(5.0)


def test_qoq_annualized():
    observations = (
        Observation(date(2025, 1, 1), 100),
        Observation(date(2025, 4, 1), 101),
    )
    result = transform_observations(observations, "qoq_ann")
    assert result[0].value == pytest.approx(4.060401)


def test_change():
    observations = (
        Observation(date(2025, 1, 1), 100),
        Observation(date(2025, 2, 1), 107),
    )
    result = transform_observations(observations, "change")
    assert result[0].value == 7
