"""Compatibility wrapper for decision tiers across partial/stale deploys.

Streamlit Cloud can briefly run a new app.py against an older imported module.
This wrapper preserves the verified-economic-edge gate even when the deployed
``build_decision_tiers`` implementation does not yet accept that keyword.

It also performs a small, fail-closed SportsCardsPro preflight for the strongest
research-ready fallback candidates. The guide is research triage only: it never
creates SOLD evidence, market value, max price or a BUY decision.
"""
from __future__ import annotations

from functools import lru_cache
import inspect
import os

from src.comp_research_workbench import fetch_sportscardspro_context


def _n(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _market_value(item):
    if item.get("valuation_display_safe") is not True:
        return None
    for key in ("market_value_estimate", "expected_resale", "estimated_market_value", "marknadsvarde"):
        if item.get(key) is not None:
            value = _n(item.get(key), -1)
            return value if value > 0 else None
    return None


def _supports_verified_economic_edge(item):
    decision = str(item.get("beslut") or item.get("decision") or item.get("recommendation") or "").upper()
    sold = int(_n(item.get("sold_comparable_count"), 0))
    identity_ok = bool(
        item.get("exact_identity_gate_supports_exact_comp_search")
        or item.get("exact_identity_gate_status") in {"READY", "EXACT", "STRONG"}
    )
    total_cost = item.get("analysis_total_cost") if item.get("analysis_total_cost") is not None else item.get("total_cost")
    total_cost = _n(total_cost, -1)
    max_total = item.get("dynamic_max_total_price")
    if max_total is None:
        max_total = item.get("max_total_price")
    max_total = _n(max_total, 0)
    market_value = _market_value(item)
    return bool(
        (decision.startswith("KÖP") or decision.startswith("KOP"))
        and sold >= 2
        and identity_ok
        and market_value is not None
        and total_cost >= 0
        and max_total > 0
        and total_cost <= max_total
    )


def _research_identity(item):
    fields = item.get("exact_identity_gate_research_identity_fields") or item.get("exact_identity_gate_identity_fields") or {}
    return dict(fields) if isinstance(fields, dict) else {}


def _research_ready(item):
    return bool(
        item.get("exact_identity_gate_supports_comp_research")
        or item.get("exact_identity_gate_supports_exact_comp_search")
        or item.get("exact_identity_gate_status") in {"SÖKBAR_TITEL", "SÖKBAR", "VERIFIERAD", "READY", "EXACT", "STRONG"}
    )


def _has_guide_context(item):
    triage = item.get("guide_triage") or item.get("price_guide_triage")
    if isinstance(triage, dict) and triage.get("status"):
        return True
    scp = item.get("sports_cards_pro") or item.get("sportscardspro_context")
    return bool(isinstance(scp, dict) and scp.get("ok"))


def _classify_guide_context(scp):
    if not isinstance(scp, dict) or not scp.get("ok"):
        return None
    try:
        raw = float(scp.get("ungraded_usd"))
    except (TypeError, ValueError):
        raw = None
    if raw is None:
        return {
            "status": "NO_RAW_GUIDE",
            "priority": 1,
            "ungraded_usd": None,
            "label": "Raw-guide saknas",
        }
    if raw <= 3.0:
        return {
            "status": "LOW_GUIDE_CONTEXT",
            "priority": 3,
            "ungraded_usd": raw,
            "label": "Låg prisguidekontext",
        }
    if raw <= 10.0:
        return {
            "status": "MODEST_GUIDE_CONTEXT",
            "priority": 2,
            "ungraded_usd": raw,
            "label": "Måttlig prisguidekontext",
        }
    return {
        "status": "MEANINGFUL_GUIDE_CONTEXT",
        "priority": 0,
        "ungraded_usd": raw,
        "label": "Högre prisguidekontext",
    }


def _identity_cache_key(identity):
    return tuple(str(identity.get(key) or "").strip() for key in (
        "player_name", "set_name", "season", "card_number", "parallel",
        "serial_denominator", "grading_company", "grade",
    ))


def _resolve_scp_token():
    token = str(os.getenv("SPORTSCARDSPRO_TOKEN") or "").strip()
    if token:
        return token
    try:
        import streamlit as st
        return str(st.secrets.get("SPORTSCARDSPRO_TOKEN") or "").strip()
    except Exception:
        return ""


@lru_cache(maxsize=512)
def _cached_guide_lookup(token, identity_key):
    keys = (
        "player_name", "set_name", "season", "card_number", "parallel",
        "serial_denominator", "grading_company", "grade",
    )
    identity = {key: value for key, value in zip(keys, identity_key) if value}
    return fetch_sportscardspro_context(identity, token=token)


def _auto_attach_guide_context(candidates, *, max_lookups=6):
    """Attach guide triage to a few strongest fallback candidates.

    Deliberately mutates candidate dictionaries in place so later views in the
    same Streamlit rerun (notably the unlock/research queue) reuse exactly the
    same triage instead of ranking stale copies. The lookup is capped and cached.
    """
    rows = list(candidates or [])
    token = _resolve_scp_token()
    if not token or max_lookups <= 0:
        return rows

    eligible = []
    for idx, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        if _has_guide_context(item):
            continue
        if int(_n(item.get("sold_comparable_count"), 0)) >= 2:
            continue
        if not _research_ready(item):
            continue
        identity = _research_identity(item)
        if not all(str(identity.get(key) or "").strip() for key in ("player_name", "set_name", "season", "card_number")):
            continue
        priority = (
            _n(item.get("deal_score"), 0)
            + min(25.0, _n(item.get("collector_worth_score"), 0) * 0.20)
            + min(20.0, _n(item.get("card_hierarchy_score"), 0) * 0.15)
        )
        eligible.append((priority, idx, identity))

    eligible.sort(reverse=True, key=lambda row: row[0])
    for _priority, idx, identity in eligible[: max(0, int(max_lookups))]:
        try:
            scp = _cached_guide_lookup(token, _identity_cache_key(identity))
        except Exception:
            continue
        triage = _classify_guide_context(scp)
        if not triage:
            continue
        rows[idx]["sports_cards_pro"] = scp
        rows[idx]["guide_triage"] = triage
        rows[idx]["price_guide_auto_prefetched"] = True

    return rows


def _special_signal(source):
    return bool(
        source.get("is_information_edge_candidate")
        or source.get("is_market_edge_candidate")
        or source.get("is_hidden_find_candidate")
        or source.get("misclassified_card_candidate")
        or source.get("mispriced_rookie_candidate")
        or source.get("is_case_hit")
        or source.get("is_short_print")
        or source.get("is_ssp")
        or source.get("is_1of1")
        or source.get("is_auto")
        or source.get("is_patch")
        or source.get("is_jersey")
    )


def _postprocess_fallback_result(result, total_limit):
    """Prefer meaningful candidates without ever emptying the fallback list.

    Weak ordinary cards may be pushed below stronger candidates, but the
    dynamic list is a relative Top N of the analysed pool.  Suppression must
    therefore never turn a non-empty candidate pool into an empty result.
    """
    if not isinstance(result, dict) or not result.get("fallback_investigate_mode"):
        return result
    out = dict(result)
    rows = list(out.get("rows") or [])
    if not rows:
        return out

    kept = []
    suppressed = []
    for row in rows:
        source = row.get("_source_item") or {}
        sold = int(_n(row.get("sold_comps"), 0))
        potential = _n(row.get("potential"), 0)
        merit = _n(row.get("structural_merit"), 0)
        investigate = _n(row.get("investigate_score"), 0)
        guide_status = str(row.get("guide_status") or "")
        weak_ordinary = (
            sold == 0
            and not _special_signal(source)
            and potential < 30
            and merit < 60
            and investigate < 50
        )
        low_guide_noise = (
            guide_status == "LOW_GUIDE_CONTEXT"
            and sold == 0
            and merit < 60
            and not _special_signal(source)
        )
        if weak_ordinary or low_guide_noise:
            suppressed.append(row)
        else:
            kept.append(row)

    kept.sort(
        key=lambda r: (
            _n(r.get("investigate_score"), 0),
            _n(r.get("structural_merit"), 0),
            _n(r.get("potential"), 0),
            bool(r.get("research_ready")),
            _n(r.get("certainty"), 0),
        ),
        reverse=True,
    )
    limit = max(0, int(total_limit or 0))
    # Fill remaining places with the best of the weak pool. They stay clearly
    # marked UNDERSÖK and never gain SOLD evidence, market value or BUY status.
    suppressed.sort(
        key=lambda r: (
            _n(r.get("investigate_score"), 0),
            _n(r.get("structural_merit"), 0),
            _n(r.get("potential"), 0),
            bool(r.get("research_ready")),
            _n(r.get("certainty"), 0),
        ),
        reverse=True,
    )
    # Preserve the quality gate whenever at least one meaningful row survives.
    # The recovery path exists specifically for the all-suppressed regression.
    fill_count = min(limit, len(suppressed)) if not kept else 0
    restored = suppressed[:fill_count]
    still_suppressed = suppressed[fill_count:]
    out["rows"] = (kept + restored)[:limit]
    out["suppressed_weak_ordinary_count"] = len(still_suppressed)
    out["suppressed_weak_ordinary_titles"] = [r.get("title") for r in still_suppressed[:10]]
    out["fallback_weak_fill_count"] = len(restored)
    if still_suppressed:
        note = str(out.get("note") or "").strip()
        out["note"] = (note + " Ordinära lågpotentialkort utan tydlig kortspecifik edge döljs från 'Bästa alternativen'.").strip()
    return out


def build_decision_tiers_compat(builder, candidates, *, total_limit=3, require_verified_economic_edge=False):
    """Call current builder, or safely adapt an older signature."""
    rows = list(candidates or [])
    if require_verified_economic_edge:
        rows = _auto_attach_guide_context(rows, max_lookups=max(6, int(total_limit or 3) * 2))

    try:
        params = inspect.signature(builder).parameters
    except (TypeError, ValueError):
        params = {}

    if "require_verified_economic_edge" in params:
        result = builder(
            rows,
            total_limit=total_limit,
            require_verified_economic_edge=require_verified_economic_edge,
        )
        return _postprocess_fallback_result(result, total_limit)

    gated = rows
    rejected_count = 0
    if require_verified_economic_edge:
        gated = [item for item in rows if _supports_verified_economic_edge(item)]
        rejected_count = len(rows) - len(gated)

    result = builder(gated, total_limit=total_limit)
    if not isinstance(result, dict):
        return result
    result = dict(result)
    result.setdefault("rejected_count", rejected_count)
    result.setdefault("rejection_reasons", {"legacy decision-tier module; compatibility gate applied": rejected_count} if rejected_count else {})
    note = str(result.get("note") or "").strip()
    compat_note = "Verified economic-edge gate applied through deploy compatibility wrapper."
    result["note"] = f"{note} {compat_note}".strip()
    return _postprocess_fallback_result(result, total_limit)
