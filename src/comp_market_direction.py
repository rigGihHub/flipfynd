"""Descriptive market direction for independent Exact sold comps.

Never changes valuation, max bid, KÖP decisions or comp eligibility.
"""
from __future__ import annotations
from datetime import datetime, timezone
from statistics import median
from typing import Any, Iterable
from src.comp_set_consistency import collapse_independent_observations


def _num(value: object) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _date(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    s = str(value).strip()
    for candidate in (s, s.replace("Z", "+00:00")):
        try:
            d = datetime.fromisoformat(candidate)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def build_comp_market_direction(exact_rows: Iterable[dict] | None) -> dict[str, Any]:
    rows = collapse_independent_observations(exact_rows)["rows"]
    points = []
    missing_date = 0
    missing_price = 0
    for row in rows:
        price = _num(row.get("price") if row.get("price") not in (None, "") else row.get("sold_price"))
        date = _date(row.get("sold_at") or row.get("sold_date") or row.get("date"))
        if date is None:
            missing_date += 1
            continue
        if price is None:
            missing_price += 1
            continue
        points.append({"date": date, "price": price})
    points.sort(key=lambda x: x["date"])
    if len(points) < 2:
        return {
            "status": "INSUFFICIENT_DATA",
            "label": "För få daterade Exact-comps",
            "count": len(points),
            "missing_date_count": missing_date,
            "missing_price_count": missing_price,
            "note": "Minst två daterade Exact-försäljningar behövs för riktning.",
        }
    prices = [x["price"] for x in points]
    moves = []
    for a, b in zip(points, points[1:]):
        diff = b["price"] - a["price"]
        moves.append(1 if diff > 0 else (-1 if diff < 0 else 0))
    up = sum(m > 0 for m in moves)
    down = sum(m < 0 for m in moves)
    flat = sum(m == 0 for m in moves)
    if up and not down:
        direction, label = "UP", "Exact-priserna har bara stigit"
    elif down and not up:
        direction, label = "DOWN", "Exact-priserna har bara fallit"
    elif up > down:
        direction, label = "MIXED_UP", "Blandat men fler uppgångar"
    elif down > up:
        direction, label = "MIXED_DOWN", "Blandat men fler nedgångar"
    else:
        direction, label = "MIXED", "Blandad prisriktning"
    first_price, latest_price = prices[0], prices[-1]
    pct_change = (latest_price - first_price) / first_price * 100.0
    recent = points[-3:]
    recent_prices = [x["price"] for x in recent]
    return {
        "status": "DESCRIBED",
        "label": label,
        "direction": direction,
        "count": len(points),
        "first_date": points[0]["date"].date().isoformat(),
        "latest_date": points[-1]["date"].date().isoformat(),
        "first_price": round(first_price, 2),
        "latest_price": round(latest_price, 2),
        "absolute_change": round(latest_price - first_price, 2),
        "pct_change": round(pct_change, 1),
        "up_moves": up,
        "down_moves": down,
        "flat_moves": flat,
        "overall_median": round(float(median(prices)), 2),
        "recent_count": len(recent_prices),
        "recent_median": round(float(median(recent_prices)), 2),
        "recent_prices": [round(float(x), 2) for x in recent_prices],
        "missing_date_count": missing_date,
        "missing_price_count": missing_price,
        "note": "Transparenslager: observerad riktning ändrar inte värdering eller köpbeslut.",
    }
