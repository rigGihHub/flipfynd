"""Exact premium valuation range for FlipFynd.

Builds a conservative observed range only from EXACT_PREMIUM sold comps already
classified by Premium Comp Hunter. It never manufactures a price from rarity,
player demand, active listings, or broad same-player comps.
"""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Any, Iterable


def _to_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _parse_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidates = [text, text.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _freshness_weight(date_value: Any, now: datetime) -> tuple[float, int | None]:
    dt = _parse_date(date_value)
    if dt is None:
        return 0.65, None
    age_days = max(0, int((now - dt).total_seconds() // 86400))
    if age_days <= 90:
        return 1.00, age_days
    if age_days <= 180:
        return 0.85, age_days
    if age_days <= 365:
        return 0.70, age_days
    return 0.55, age_days


def _weighted_median(rows: list[dict[str, Any]]) -> float:
    ordered = sorted(rows, key=lambda row: row["price"])
    total = sum(float(row["weight"]) for row in ordered)
    threshold = total / 2
    running = 0.0
    for row in ordered:
        running += float(row["weight"])
        if running >= threshold:
            return float(row["price"])
    return float(ordered[-1]["price"])


def build_exact_premium_valuation(
    exact_comps: Iterable[dict[str, Any]] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return an observed premium valuation range from exact sold comps only."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    rows: list[dict[str, Any]] = []
    for comp in list(exact_comps or []):
        price = _to_float(comp.get("price"))
        if price is None:
            continue
        weight, age_days = _freshness_weight(comp.get("date"), now)
        rows.append({
            "price": price,
            "weight": weight,
            "age_days": age_days,
            "date": comp.get("date"),
            "title": comp.get("title"),
            "url": comp.get("url"),
            "platform": comp.get("platform"),
        })

    if len(rows) < 2:
        return {
            "active": bool(rows),
            "safe_for_display": False,
            "count": len(rows),
            "low": None,
            "base": None,
            "high": None,
            "spread_pct": None,
            "fresh_count": sum(1 for r in rows if r["age_days"] is not None and r["age_days"] <= 180),
            "observations": rows,
            "note": "Minst två exakta premiumförsäljningar med pris behövs för ett premiumintervall.",
        }

    prices = sorted(r["price"] for r in rows)
    low = float(prices[0])
    high = float(prices[-1])
    base = _weighted_median(rows)
    spread_pct = round(((high - low) / base) * 100, 1) if base > 0 else None
    fresh_count = sum(1 for r in rows if r["age_days"] is not None and r["age_days"] <= 180)

    # With very wide dispersion, keep the evidence visible but warn that the
    # base point is not a tight market estimate.
    tightness = "tight" if spread_pct is not None and spread_pct <= 25 else "medium" if spread_pct is not None and spread_pct <= 60 else "wide"
    confidence = "hög" if len(rows) >= 4 and tightness == "tight" and fresh_count >= 2 else "medel" if len(rows) >= 3 and tightness != "wide" else "låg"

    return {
        "active": True,
        "safe_for_display": True,
        "count": len(rows),
        "low": round(low),
        "base": round(base),
        "high": round(high),
        "spread_pct": spread_pct,
        "fresh_count": fresh_count,
        "tightness": tightness,
        "confidence": confidence,
        "observations": sorted(rows, key=lambda r: (r["age_days"] is None, r["age_days"] if r["age_days"] is not None else 10**9)),
        "note": "Intervallet bygger endast på exakta premium-sold comps. Färskare försäljningar väger tyngre i basvärdet; låg/hög är observerade prisgränser, inte prognoser.",
    }
