from datetime import datetime, timezone

from src.premium_valuation import build_exact_premium_valuation


def test_requires_two_exact_prices():
    out = build_exact_premium_valuation([{"price": 500, "date": "2026-08-01"}])
    assert out["safe_for_display"] is False


def test_observed_low_high_are_not_invented():
    out = build_exact_premium_valuation([
        {"price": 500, "date": "2026-08-01"},
        {"price": 700, "date": "2026-08-15"},
        {"price": 600, "date": "2026-08-20"},
    ], now=datetime(2026, 9, 3, tzinfo=timezone.utc))
    assert out["low"] == 500
    assert out["high"] == 700
    assert out["base"] == 600


def test_fresh_sales_weigh_more_in_base_value():
    out = build_exact_premium_valuation([
        {"price": 1000, "date": "2023-01-01"},
        {"price": 500, "date": "2026-08-20"},
        {"price": 520, "date": "2026-08-25"},
    ], now=datetime(2026, 9, 3, tzinfo=timezone.utc))
    assert out["base"] in {500, 520}
    assert out["fresh_count"] == 2


def test_undated_sales_are_kept_but_downweighted():
    out = build_exact_premium_valuation([
        {"price": 400},
        {"price": 450, "date": "2026-08-20"},
    ], now=datetime(2026, 9, 3, tzinfo=timezone.utc))
    assert out["safe_for_display"] is True
    assert out["count"] == 2


def test_nonpositive_prices_are_ignored():
    out = build_exact_premium_valuation([
        {"price": 0, "date": "2026-08-20"},
        {"price": -1, "date": "2026-08-20"},
        {"price": 300, "date": "2026-08-20"},
    ])
    assert out["count"] == 1
    assert out["safe_for_display"] is False
