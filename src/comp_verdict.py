"""Comp Verdict for FlipFynd.

Turns Exact Comp Hunter evidence into a plain-language evidence verdict.
It never creates a market price and does not alter profit, ROI, max bid or buy
recommendations automatically.
"""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Any


def _price(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _parse_date(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def build_comp_verdict(hunt: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Summarise exact-comp evidence without changing the underlying valuation."""
    exact = list(hunt.get("exact") or [])
    near = list(hunt.get("near") or [])
    rejected = list(hunt.get("rejected") or [])
    unlocked = bool(hunt.get("unlocked"))

    if not unlocked:
        return {
            "score": 0,
            "level": "låst",
            "verdict": "Otillräckligt underlag för comp-dom",
            "reasons": ["exakt comp-sökning är inte upplåst"],
            "exact_count": 0,
            "near_count": 0,
            "price_median": None,
            "price_low": None,
            "price_high": None,
            "relative_spread": None,
            "recent_exact_count": 0,
            "supports_safe_max_bid": False,
            "note": "Comp Verdict organiserar bevis och ändrar inte värdering eller maxbud automatiskt.",
        }

    prices = [_price(x.get("price")) for x in exact]
    prices = [p for p in prices if p is not None]
    exact_count = len(exact)
    near_count = len(near)
    score = 10
    reasons: list[str] = []

    if exact_count == 0:
        score = 15
        verdict = "Inga exakta avslut – värderingen är inte comp-verifierad"
        reasons.append("ingen exakt såld comp finns i den lokala historiken")
    elif exact_count == 1:
        score = 38
        verdict = "För få exakta avslut för säker värdering"
        reasons.append("endast ett exakt verifierat avslut")
    elif exact_count == 2:
        score = 58
        verdict = "Värderingen har visst stöd men fler exakta avslut behövs"
        reasons.append("två exakta verifierade avslut")
    elif exact_count >= 5:
        score = 84
        verdict = "Värderingen är starkt underbyggd"
        reasons.append(f"{exact_count} exakta verifierade avslut")
    else:
        score = 74
        verdict = "Värderingen har bra stöd av exakta avslut"
        reasons.append(f"{exact_count} exakta verifierade avslut")

    med = median(prices) if prices else None
    low = min(prices) if prices else None
    high = max(prices) if prices else None
    spread = ((high - low) / med) if med and len(prices) >= 2 else None

    if spread is not None:
        if spread <= 0.20:
            score += 10
            reasons.append("de exakta slutpriserna ligger tätt")
        elif spread <= 0.40:
            score += 4
            reasons.append("prisspridningen mellan exakta avslut är rimlig")
        elif spread > 0.70:
            score -= 24
            verdict = "Marknaden är för spretig för säkert maxbud"
            reasons.append("de exakta slutpriserna har mycket stor spridning")
        elif spread > 0.50:
            score -= 12
            reasons.append("de exakta slutpriserna har stor spridning")

    if rejected:
        penalty = min(12, len(rejected) * 2)
        score -= penalty
        reasons.append(f"{len(rejected)} historiska poster avvisades p.g.a. identitetskonflikt")

    if near_count and exact_count < 3:
        reasons.append(f"{near_count} nära avslut finns som sekundärt stöd, men räknas inte som exakt kort")

    now = now or datetime.now(timezone.utc)
    recent = 0
    dated = 0
    for comp in exact:
        dt = _parse_date(comp.get("sold_at") or comp.get("sold_date") or comp.get("date"))
        if not dt:
            continue
        dated += 1
        age = (now - dt).days
        if 0 <= age <= 180:
            recent += 1
    if dated:
        if recent >= 3:
            score += 5
            reasons.append(f"{recent} exakta avslut är högst 180 dagar gamla")
        elif recent == 0:
            score -= 6
            reasons.append("inga daterade exakta avslut är högst 180 dagar gamla")

    score = int(max(0, min(100, round(score))))
    if exact_count == 0:
        level = "mycket låg"
    elif score >= 80 and exact_count >= 3 and (spread is None or spread <= 0.40):
        level = "hög"
        verdict = "Värderingen är starkt underbyggd"
    elif score >= 60 and exact_count >= 2 and (spread is None or spread <= 0.55):
        level = "medel–hög"
    elif score >= 40:
        level = "medel"
    else:
        level = "låg"

    supports_safe_max_bid = bool(
        exact_count >= 3
        and score >= 70
        and (spread is None or spread <= 0.45)
    )
    if supports_safe_max_bid:
        reasons.append("comp-underlaget är tillräckligt stabilt för att stödja ett försiktigt maxbud")
    elif exact_count:
        reasons.append("comp-underlaget bör inte ensamt användas för ett aggressivt maxbud")

    return {
        "score": score,
        "level": level,
        "verdict": verdict,
        "reasons": reasons,
        "exact_count": exact_count,
        "near_count": near_count,
        "price_median": round(med, 2) if med is not None else None,
        "price_low": round(low, 2) if low is not None else None,
        "price_high": round(high, 2) if high is not None else None,
        "relative_spread": round(spread, 4) if spread is not None else None,
        "recent_exact_count": recent,
        "supports_safe_max_bid": supports_safe_max_bid,
        "note": "Comp Verdict organiserar bevis och ändrar inte värdering eller maxbud automatiskt.",
    }
