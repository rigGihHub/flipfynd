"""Plan how FlipFynd should acquire real SOLD evidence next.

This module does not fetch remote data. It turns the source registry into an
auditable priority plan so the product can distinguish three different jobs:
1) automatic ingestion that is actually available,
2) explicit import/capture of verified sales,
3) manual research destinations that may produce evidence later.

The planner deliberately favours direct realised-sales sources over price guides.
"""
from __future__ import annotations

from src.sold_source_registry import sold_source_registry


def _source_score(source: dict) -> int:
    score = 0
    evidence = str(source.get("evidence_type") or "")
    status = str(source.get("status") or "")
    if evidence == "DIRECT_REALIZED_SALES":
        score += 60
    elif evidence in {"MARKETPLACE_SALES_DATABASE", "MULTI_MARKET_SALES_DATABASE", "SALES_RESEARCH_AGGREGATOR"}:
        score += 35
    elif evidence == "AGGREGATED_PRICE_GUIDE":
        score += 10
    if source.get("automated_ingestion"):
        score += 35
    if status == "RESEARCH_AND_EXPLICIT_IMPORT":
        score += 20
    elif status == "RESEARCH_ONLY":
        score += 5
    if source.get("key") == "tradera_sold":
        score += 8
    if source.get("key") == "ebay_product_research":
        score += 6
    return score


def _next_action(source: dict) -> str:
    if source.get("automated_ingestion"):
        return "Kör automatisk import och routa varje rad genom exact-identity/SOLD-intake."
    status = str(source.get("status") or "")
    evidence = str(source.get("evidence_type") or "")
    if status == "RESEARCH_AND_EXPLICIT_IMPORT":
        return "Prioritera explicit export/import av verifierade avslut; importera aldrig aktiva eller osålda annonser."
    if evidence == "DIRECT_REALIZED_SALES":
        return "Använd som primär researchkälla och fånga verifierade individuella sales med exakt kortidentitet."
    if evidence in {"MULTI_MARKET_SALES_DATABASE", "MARKETPLACE_SALES_DATABASE", "SALES_RESEARCH_AGGREGATOR"}:
        return "Använd som sekundär kontrollkälla; endast individuellt verifierade realiserade sales får bli exact SOLD."
    return "Använd endast som pris-/marknadskontext, aldrig som exact SOLD-evidens."


def build_sold_acquisition_strategy(limit: int = 6) -> dict:
    sources = sold_source_registry()
    rows = []
    for source in sources:
        row = dict(source)
        row["priority_score"] = _source_score(source)
        row["next_action"] = _next_action(source)
        row["can_create_exact_sold_automatically"] = bool(
            source.get("automated_ingestion") and source.get("evidence_type") == "DIRECT_REALIZED_SALES"
        )
        row["requires_human_verification"] = not row["can_create_exact_sold_automatically"]
        rows.append(row)
    rows.sort(key=lambda row: (row["priority_score"], row.get("label") or ""), reverse=True)
    chosen = rows[: max(0, int(limit))]
    direct = [row for row in rows if row.get("evidence_type") == "DIRECT_REALIZED_SALES"]
    automated = [row for row in rows if row.get("automated_ingestion")]
    return {
        "rows": chosen,
        "direct_realized_source_count": len(direct),
        "automated_source_count": len(automated),
        "manual_or_explicit_source_count": len(rows) - len(automated),
        "primary_goal": "Få in de första 50–100 verifierade exact SOLD-comps utan att blanda in aktiva annonser eller prisguider.",
        "status": "AUTOMATED_INGESTION_AVAILABLE" if automated else "HUMAN_VERIFIED_ACQUISITION_REQUIRED",
        "note": (
            "Planen prioriterar verkliga realiserade sales. Prisguider får bara hjälpa triage och sanity check. "
            "Varje importerad sale måste fortfarande passera FlipFynds identitets- och SOLD-intake."
        ),
    }
