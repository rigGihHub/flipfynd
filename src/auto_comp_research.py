"""Batch-oriented, fail-closed comp research runner.

The runner automates everything FlipFynd can do safely without inventing SOLD
history: it derives exact identity, scans the local sold library for matching
verified sales, builds source-specific research links, and optionally fetches
SportsCardsPro guide context when an official API token is configured.

It never scrapes marketplaces and never promotes active listings or price-guide
values into exact SOLD evidence.
"""
from __future__ import annotations

from typing import Iterable

from src.comp_research_workbench import build_research_links, fetch_sportscardspro_context
from src.exact_comp_hunter import hunt_exact_comps
from src.research_query_ladder import build_research_query_ladder
from src.research_candidate_matcher import rank_research_candidates
from src.research_verification_priority import prioritize_verification_candidates


def _clean(value):
    return " ".join(str(value or "").strip().split())


def identity_from_item(item: dict | None, *, research: bool = False) -> dict:
    """Return analyzer-produced identity fields.

    Research mode may use title-recovered fields explicitly marked research-only.
    Strict exact-SOLD matching still uses the decision-grade identity fields.
    """
    item = item or {}
    if research:
        fields = item.get("exact_identity_gate_research_identity_fields") or {}
        if isinstance(fields, dict) and any(fields.get(k) for k in ("player_name", "set_name", "season", "card_number")):
            return dict(fields)
    fields = item.get("exact_identity_gate_identity_fields") or {}
    return dict(fields) if isinstance(fields, dict) else {}


def identity_ready(item: dict | None) -> bool:
    """Strict decision-grade exact identity."""
    item = item or {}
    return bool(
        item.get("exact_identity_gate_supports_exact_comp_search")
        or item.get("exact_identity_gate_status") in {"READY", "EXACT", "STRONG", "VERIFIERAD", "SÖKBAR"}
    )


def research_identity_ready(item: dict | None) -> bool:
    """Search-grade identity; may build queries but never valuation by itself."""
    item = item or {}
    return bool(
        item.get("exact_identity_gate_supports_comp_research")
        or identity_ready(item)
        or item.get("exact_identity_gate_status") == "SÖKBAR_TITEL"
    )


def _identity_candidate(item: dict) -> dict:
    return {
        "verified_identity": identity_ready(item),
        "research_identity": research_identity_ready(item),
        "identity_fields": identity_from_item(item, research=False),
    }


def research_one(item: dict, sold_records: Iterable[dict] | None = None, *, scp_token: str | None = None) -> dict:
    """Run safe automated research for one already-analyzed listing."""
    title = _clean(item.get("titel") or item.get("title")) or "Okänt kort"
    ready = identity_ready(item)
    research_ready = research_identity_ready(item)
    identity = identity_from_item(item, research=(research_ready and not ready))
    local = hunt_exact_comps(_identity_candidate(item), observed_records=sold_records or [])
    links = build_research_links(identity) if (identity and research_ready) else {"ready": False, "links": [], "query": None, "missing_fields": []}
    query_ladder = build_research_query_ladder(identity) if (identity and research_ready) else {"ready": False, "queries": []}
    candidate_matches = rank_research_candidates(identity, sold_records or [], limit=8) if (identity and research_ready) else []
    verification_queue = prioritize_verification_candidates(candidate_matches, limit=5)

    scp = None
    if scp_token and research_ready:
        try:
            scp = fetch_sportscardspro_context(identity, token=scp_token)
        except Exception as exc:  # network/API failures are research status, never fatal app errors
            scp = {"ok": False, "status": "REQUEST_FAILED", "error": str(exc)}

    exact_count = int(local.get("exact_sold_count") or 0)
    near_count = int(local.get("near_sold_count") or 0)
    missing_sales = max(0, 2 - exact_count)
    if not research_ready:
        status = "IDENTITY_FIRST"
        next_action = "Strukturera spelare, set, säsong och kortnummer innan automatisk comp-jakt."
    elif not ready:
        status = "RESEARCH_ONLY"
        next_action = "Sök efter möjliga comps från den strukturerade titeln; verifiera identiteten innan någon sale får räknas som exact."
    elif missing_sales == 0:
        status = "LOCAL_THRESHOLD_MET"
        next_action = "Minst 2 verifierade exact SOLD finns redan i biblioteket. Kör om analysen för värdering/maxpris."
    elif missing_sales == 1:
        status = "ONE_EXACT_SALE_NEEDED"
        next_action = "Hitta och verifiera 1 ytterligare exact SOLD från researchlänkarna."
    else:
        status = "TWO_EXACT_SALES_NEEDED"
        next_action = "Hitta och verifiera minst 2 exact SOLD. Börja med eBay Sold och Tradera/Fanatics som oberoende kontroll."

    return {
        "title": title,
        "url": item.get("lank") or item.get("url"),
        "identity_ready": ready,
        "research_identity_ready": research_ready,
        "identity": identity,
        "query": links.get("query"),
        "research_links": links.get("links") or [],
        "query_ladder": query_ladder.get("queries") or [],
        "candidate_matches": candidate_matches,
        "verification_queue": verification_queue,
        "exact_sold_count": exact_count,
        "near_sold_count": near_count,
        "missing_exact_sales": missing_sales,
        "status": status,
        "next_action": next_action,
        "sports_cards_pro": scp,
        "creates_sold_evidence": False,
        "creates_buy_decision": False,
    }


def run_auto_comp_research(items: Iterable[dict] | None, sold_records: Iterable[dict] | None = None, *, limit: int = 5, scp_token: str | None = None) -> dict:
    """Research up to ``limit`` prioritized items in one click.

    The function intentionally returns a research pack rather than mutating the
    sold library. External sales must still be explicitly verified/imported.
    """
    selected = [x for x in (items or []) if isinstance(x, dict)][: max(0, int(limit))]
    rows = [research_one(item, sold_records=sold_records or [], scp_token=scp_token) for item in selected]
    ready = sum(1 for row in rows if row["identity_ready"])
    research_ready = sum(1 for row in rows if row.get("research_identity_ready"))
    threshold = sum(1 for row in rows if row["exact_sold_count"] >= 2)
    one_away = sum(1 for row in rows if row["missing_exact_sales"] == 1 and row["identity_ready"])
    return {
        "rows": rows,
        "processed_count": len(rows),
        "identity_ready_count": ready,
        "research_identity_ready_count": research_ready,
        "threshold_met_count": threshold,
        "one_sale_away_count": one_away,
        "note": (
            "Automatisk comp-jakt skannar lokalt verifierad SOLD-historik, bygger exakta researchlänkar och kan hämta "
            "SportsCardsPro-guide via officiellt API. Query ladder provar även säkra alternativa sökfraser när marknadsplatser namnger samma kort olika. "
            "Candidate matcher rankar möjliga träffar med hårda konflikter för spelare, kortnummer, säsong, parallel och premiumegenskaper. "
            "Verification queue väljer sedan vilka starka träffar som är mest värda att kontrollera först och försöker sprida arbetet över oberoende källor. "
            "Den skrapar inte marknadsplatser och skapar aldrig SOLD eller KÖP utan verifiering."
        ),
    }
