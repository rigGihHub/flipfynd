"""Decision-grade quality guard for already verified Exact sold comps.

The guard does not create prices or broaden comp eligibility. It only decides
whether an already Exact-only evidence set is sufficiently current, numerous
and stable to be called decision-grade. Thresholds deliberately reuse existing
FlipFynd Comp Verdict safety rules: 3 exact comps, <=45% relative spread and a
180-day recency window.
"""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Any, Iterable

from src.comp_set_consistency import collapse_independent_observations
from src.comp_source_diversity import build_comp_source_diversity
from src.comp_recency_transparency import build_comp_recency_transparency
from src.comp_market_direction import build_comp_market_direction
from src.market_direction_evidence import build_market_direction_evidence


MIN_EXACT_FOR_DECISION = 3
MAX_RELATIVE_SPREAD = 0.45
RECENT_DAYS = 180


def _num(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _parse_date(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    candidates = (text, text.replace("Z", "+00:00"))
    for candidate in candidates:
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


def build_comp_quality_guard(exact_rows: Iterable[dict] | None, *, now: datetime | None = None) -> dict[str, Any]:
    raw_rows = list(exact_rows or [])
    consistency = collapse_independent_observations(raw_rows)
    rows = consistency["rows"]
    source_diversity = build_comp_source_diversity(raw_rows)
    now = now or datetime.now(timezone.utc)
    recency_transparency = build_comp_recency_transparency(raw_rows, now=now)
    market_direction = build_comp_market_direction(raw_rows)
    market_direction_evidence = build_market_direction_evidence(raw_rows)

    prices = [_num(r.get("price") if r.get("price") not in (None, "") else r.get("sold_price")) for r in rows]
    prices = [p for p in prices if p is not None]
    med = median(prices) if prices else None
    low = min(prices) if prices else None
    high = max(prices) if prices else None
    spread = ((high - low) / med) if med and len(prices) >= 2 else None

    dated = 0
    recent = 0
    future_dates = 0
    ages: list[int] = []
    for row in rows:
        dt = _parse_date(row.get("sold_at") or row.get("sold_date") or row.get("date"))
        if not dt:
            continue
        dated += 1
        age = (now - dt).days
        if age < 0:
            future_dates += 1
            continue
        ages.append(age)
        if age <= RECENT_DAYS:
            recent += 1

    blockers: list[str] = []
    warnings: list[str] = []

    if len(rows) < MIN_EXACT_FOR_DECISION:
        blockers.append(f"bara {len(rows)} Exact-comps; minst {MIN_EXACT_FOR_DECISION} krävs för beslutsstarkt stöd")
    if len(prices) < MIN_EXACT_FOR_DECISION:
        blockers.append(f"bara {len(prices)} Exact-comps har användbart sålt pris")
    if spread is not None and spread > MAX_RELATIVE_SPREAD:
        blockers.append(f"prisspridningen är {spread*100:.0f}%, över befintlig säkerhetsgräns {MAX_RELATIVE_SPREAD*100:.0f}%")
    if future_dates:
        blockers.append(f"{future_dates} comp-datum ligger i framtiden och kan inte användas som historiskt stöd")
    if dated == 0 and rows:
        blockers.append("försäljningsdatum saknas; färskheten kan inte verifieras")
    elif recent == 0 and dated:
        blockers.append(f"inga daterade Exact-comps är högst {RECENT_DAYS} dagar gamla")
    elif dated < len(rows):
        warnings.append(f"datum saknas för {len(rows)-dated} av {len(rows)} Exact-comps")

    if source_diversity.get("status") == "CONCENTRATED":
        warnings.append("comp-underlaget är källkoncentrerat; se Source Diversity för detaljer")

    if consistency["duplicate_count"]:
        warnings.append(
            f"{consistency['duplicate_count']} upprepad comp-post kollapsades; "
            f"{consistency['independent_count']} oberoende observationer återstår"
        )

    if not rows:
        status = "NO_EXACT_COMPS"
        label = "Inga Exact-comps"
    elif blockers:
        if len(rows) < MIN_EXACT_FOR_DECISION or len(prices) < MIN_EXACT_FOR_DECISION:
            status = "THIN"
            label = "För tunt underlag"
        elif spread is not None and spread > MAX_RELATIVE_SPREAD:
            status = "DISPERSED"
            label = "För spretiga priser"
        elif dated == 0:
            status = "MISSING_DATES"
            label = "Datum saknas"
        elif recent == 0:
            status = "STALE"
            label = "För gamla comps"
        else:
            status = "BLOCKED"
            label = "Kvalitetsgranskning krävs"
    else:
        status = "READY"
        label = "Beslutsstarkt comp-underlag"

    return {
        "status": status,
        "label": label,
        "decision_grade": status == "READY",
        "exact_count": len(rows),
        "raw_exact_count": consistency["raw_count"],
        "independent_exact_count": consistency["independent_count"],
        "duplicate_observation_count": consistency["duplicate_count"],
        "duplicate_clusters": consistency["duplicate_clusters"],
        "priced_count": len(prices),
        "dated_count": dated,
        "recent_count": recent,
        "median_price": round(med, 2) if med is not None else None,
        "price_low": round(low, 2) if low is not None else None,
        "price_high": round(high, 2) if high is not None else None,
        "relative_spread": round(spread, 4) if spread is not None else None,
        "oldest_age_days": max(ages) if ages else None,
        "newest_age_days": min(ages) if ages else None,
        "blockers": blockers,
        "warnings": warnings,
        "source_diversity": source_diversity,
        "recency_transparency": recency_transparency,
        "market_direction": market_direction,
        "market_direction_evidence": market_direction_evidence,
        "rules": {
            "min_exact": MIN_EXACT_FOR_DECISION,
            "max_relative_spread": MAX_RELATIVE_SPREAD,
            "recent_days": RECENT_DAYS,
        },
        "note": "Guardet skapar inget pris och gör aldrig Near/Player-only till värderingsgrund. Det granskar bara oberoende, redan verifierade Exact-comps efter att upprepade observationer kollapsats konservativt.",
    }
