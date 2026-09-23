import pytest

from macrobot.alerts import condition_is_true


@pytest.mark.parametrize(
    ("operator", "value", "threshold", "expected"),
    [
        ("above", 5.1, 5.0, True),
        ("above", 5.0, 5.0, False),
        ("below", 1.9, 2.0, True),
        ("below", 2.0, 2.0, False),
    ],
)
def test_condition(operator, value, threshold, expected):
    assert condition_is_true(operator, value, threshold) is expected

