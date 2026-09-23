from datetime import date

from macrobot.timeutils import parse_period_date, period_start


def test_parse_quarter():
    assert parse_period_date("2026-Q3") == date(2026, 7, 1)


def test_period_start_years():
    assert period_start("5y", date(2026, 9, 22)) == date(2021, 9, 22)

