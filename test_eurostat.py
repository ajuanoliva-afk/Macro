from datetime import date

from macrobot.clients.eurostat import decode_jsonstat, format_since_time_period


def test_decode_jsonstat_multiple_geos_and_sparse_values():
    payload = {
        "id": ["geo", "time"],
        "size": [2, 2],
        "value": {"0": 1.0, "1": 2.0, "3": 4.0},
        "dimension": {
            "geo": {"category": {"index": {"DE": 0, "ES": 1}}},
            "time": {
                "category": {"index": {"2025-01": 0, "2025-02": 1}}
            },
        },
    }
    rows = decode_jsonstat(payload)
    assert rows == [
        {"geo": "DE", "time": "2025-01", "value": 1.0},
        {"geo": "DE", "time": "2025-02", "value": 2.0},
        {"geo": "ES", "time": "2025-02", "value": 4.0},
    ]


def test_format_since_time_period_matches_dataset_frequency():
    value = date(2026, 9, 22)
    assert format_since_time_period(value, "M") == "2026-09"
    assert format_since_time_period(value, "Q") == "2026-Q3"
    assert format_since_time_period(value, "A") == "2026"
