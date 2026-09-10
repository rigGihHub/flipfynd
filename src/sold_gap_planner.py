"""Prioritise sold-data research gaps for current FlipFynd candidates.

The planner uses only existing structured candidate identity and verified sold
records. It never infers card identity from listing titles, estimates a value,
or upgrades a buy decision.
"""
from __future__ import annotations

import re
from collections import Counter

from src.sold_comp_intake import review_sold_comp_intake

CORE_FIELDS = ("player_name", "set_name", "season", "card_number")
OPTIONAL_VARIANT_FIELDS = ("parallel", "serial_denominator", "grading_company", "grade")


def _norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _candidate_identity(candidate):
    gate = candidate.get("exact_identity_gate_identity_fields") or {}
    identity = {}
    for field in CORE_FIELDS + OPTIONAL_VARIANT_FIELDS:
        value = gate.get(field)
        if value in (None, ""):
            value = candidate.get(field)
        if value not in (None, ""):
            identity[field] = value
    return identity


def _identity_key(identity):
    if not all(identity.get(field) not in (None, "") for field in CORE_FIELDS):
        return None
    base = tuple(_norm(identity.get(field)) for field in CORE_FIELDS)
    optional = tuple(_norm(identity.get(field)) for field in OPTIONAL_VARIANT_FIELDS)
    return base + optional


def _sold_identity(record):
    review = review_sold_comp_intake(record)
    if not review.get("exact_identity_ready"):
        return None
    return {field: record.get(field) for field in CORE_FIELDS + OPTIONAL_VARIANT_FIELDS if record.get(field) not in (None, "")}


def _priority(candidate):
    """Reuse existing scores only; no new opportunity model is introduced."""
    for field in ("opportunity_priority_score", "deal_score", "rank_score"):
        try:
            return float(candidate.get(field) or 0)
        except (TypeError, ValueError):
            continue
    return 0.0


def build_sold_research_queue(candidates, sold_records, *, limit=10):
    exact_counter = Counter()
    for record in sold_records or []:
        identity = _sold_identity(record) if isinstance(record, dict) else None
        if identity:
            key = _identity_key(identity)
            if key:
                exact_counter[key] += 1

    rows = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        identity = _candidate_identity(candidate)
        missing = [field for field in CORE_FIELDS if identity.get(field) in (None, "")]
        key = _identity_key(identity)

        if missing:
            status = "IDENTITY_FIRST"
            exact_count = 0
            action = "Verifiera kortets identitet innan sold-research."
        else:
            exact_count = int(exact_counter.get(key, 0))
            if exact_count == 0:
                status = "NO_EXACT_SOLD"
                action = "Sök verifierade avslut för exakt kort."
            elif exact_count == 1:
                status = "THIN_EXACT_SOLD"
                action = "Sök fler verifierade avslut för exakt kort."
            else:
                status = "HAS_EXACT_SOLD"
                action = "Exakt sold-underlag finns redan."

        rows.append({
            "title": candidate.get("titel") or candidate.get("title") or "Okänd annons",
            "url": candidate.get("lank") or candidate.get("url"),
            "decision": candidate.get("beslut") or candidate.get("decision"),
            "status": status,
            "action": action,
            "missing_identity_fields": missing,
            "exact_sold_count": exact_count,
            "identity": identity,
            "priority_score": _priority(candidate),
        })

    status_order = {
        "NO_EXACT_SOLD": 0,
        "THIN_EXACT_SOLD": 1,
        "IDENTITY_FIRST": 2,
        "HAS_EXACT_SOLD": 3,
    }
    rows.sort(key=lambda row: (
        status_order.get(row["status"], 9),
        -row["priority_score"],
        row["title"],
    ))

    limited = rows[:max(0, int(limit))]
    counts = Counter(row["status"] for row in rows)
    return {
        "rows": limited,
        "total_candidates": len(rows),
        "no_exact_sold_count": counts["NO_EXACT_SOLD"],
        "thin_exact_sold_count": counts["THIN_EXACT_SOLD"],
        "identity_first_count": counts["IDENTITY_FIRST"],
        "has_exact_sold_count": counts["HAS_EXACT_SOLD"],
        "note": "Kön använder bara verifierad exact-ready sold-data och strukturerad kortidentitet.",
    }
