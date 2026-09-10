"""Single source of truth for shipping display and calculation provenance.

Actual listing shipping always wins. Zero is valid free shipping. When actual
shipping is missing/invalid, FlipFynd may use its existing cautious assumption,
but the result is explicitly marked as assumed.
"""
from __future__ import annotations

DEFAULT_ASSUMED_SHIPPING = 29.0


def _valid_nonnegative(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def resolve_shipping(item: dict | None, *, default=DEFAULT_ASSUMED_SHIPPING) -> dict:
    item = item or {}
    raw = item.get("frakt")
    if _valid_nonnegative(raw):
        return {
            "shipping": float(raw),
            "known": True,
            "source": "listing",
            "label": "Frakt",
        }

    assumption = item.get("max_price_shipping_assumption")
    if _valid_nonnegative(assumption):
        return {
            "shipping": float(assumption),
            "known": False,
            "source": "analysis_assumption",
            "label": "Antagen frakt",
        }

    return {
        "shipping": float(default),
        "known": False,
        "source": "default_assumption",
        "label": "Antagen frakt",
    }
