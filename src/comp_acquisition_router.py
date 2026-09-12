"""Plan the next exact-comp research step from observed source coverage.

This module does not call or scrape external marketplaces. It looks only at
already-ingested exact sold evidence and tells the UI which source should be
checked next. The goal is to avoid repeatedly researching the same source while
Tradera/local or independent international evidence is still missing.
"""
from __future__ import annotations

from src.comp_source_intelligence import build_comp_research_plan
from src.sold_research_assist import build_exact_research_query
from src.multi_source_comp_consensus import build_multi_source_consensus


PRIMARY_SOURCE_GROUPS = (
    ("tradera", "Tradera"),
    ("ebay", "eBay"),
    ("independent", "Oberoende sekundär marknad"),
)


def _norm(value) -> str:
    return " ".join(str(value or "").casefold().strip().split())


def _source_group(source: str) -> str:
    text = _norm(source)
    if "tradera" in text:
        return "tradera"
    if "ebay" in text:
        return "ebay"
    if any(token in text for token in ("card ladder", "fanatics", "comc", "130 point", "130point")):
        return "independent"
    return "other"


def _find_plan_row(plan: dict, key: str) -> dict | None:
    return next((row for row in plan.get("sources", []) if row.get("key") == key), None)


def build_comp_acquisition_router(identity: dict | None, records) -> dict:
    """Return source coverage and one best next research action.

    A source quorum is intentionally stricter than the minimum two exact sales:
    at least two exact sales from at least two source groups are required. This
    is a research-quality signal only and does not itself create a valuation or
    BUY decision.
    """
    exact_query = build_exact_research_query(identity or {})
    plan = build_comp_research_plan(identity or {})
    plan["ready"] = bool(exact_query.get("ready"))
    consensus = build_multi_source_consensus(identity or {}, records or [])

    groups = {key: {"key": key, "label": label, "count": 0} for key, label in PRIMARY_SOURCE_GROUPS}
    groups["other"] = {"key": "other", "label": "Övrig verifierad källa", "count": 0}
    for row in consensus.get("accepted") or []:
        group = _source_group(row.get("source"))
        groups[group]["count"] += 1

    exact_count = int(consensus.get("exact_sold_count") or 0)
    represented = [g for g in groups.values() if g["count"] > 0 and g["key"] != "other"]
    source_quorum = exact_count >= 2 and len(represented) >= 2

    next_key = None
    reason = ""
    if not plan.get("ready"):
        status = "IDENTITY_NOT_READY"
        reason = "Exakt comp-research väntar tills spelare, set, säsong och kortnummer är strukturerade."
    elif groups["tradera"]["count"] == 0:
        status = "SEARCH_LOCAL"
        next_key = "tradera_sold"
        reason = "Saknar svensk exact SOLD. Kontrollera Tradera först för lokal prisbild och faktisk svensk efterfrågan."
    elif exact_count < 2 or groups["ebay"]["count"] == 0:
        status = "SEARCH_EBAY"
        next_key = "ebay_sold_search"
        reason = "Lägg till färska internationella exact SOLD från eBay innan prisbilden bedöms som robust."
    elif len(represented) < 2:
        status = "DIVERSIFY_SOURCE"
        next_key = "card_ladder"
        reason = "Exact SOLD finns men nästan allt kommer från samma marknad. Sök en oberoende sekundär källa."
    else:
        status = "SOURCE_QUORUM_REACHED"
        reason = "Minst två exact SOLD och minst två oberoende källgrupper finns. Fortsatt research är frivillig kontroll, inte ett krav."

    next_source = _find_plan_row(plan, next_key) if next_key else None
    coverage = [groups[key] for key, _ in PRIMARY_SOURCE_GROUPS]

    return {
        "status": status,
        "ready": bool(plan.get("ready")),
        "query": plan.get("query"),
        "exact_sold_count": exact_count,
        "source_count": int(consensus.get("source_count") or 0),
        "source_quorum": source_quorum,
        "coverage": coverage,
        "next_source": next_source,
        "reason": reason,
        "confidence": consensus.get("confidence"),
        "note": "Källtäckning mäter researchkvalitet. Den skapar inte marknadsvärde eller KÖP och aktiva annonser räknas aldrig som SOLD.",
    }
