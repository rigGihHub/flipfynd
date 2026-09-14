"""Fast, conservative triage for live same-seller inventory.

This layer is intentionally a routing aid, not a purchase engine. It runs the
existing fast analyser on a capped number of seller listings and ranks which
ones deserve a full analysis next. It never upgrades an unverified listing to a
BUY merely because shipping may be shared.
"""
from __future__ import annotations

from typing import Callable, Iterable

from src.seller_identity import apply_seller_metadata, seller_alias, seller_id, seller_url
from src.seller_collector_signals import collector_signals


def _text(item: dict) -> str:
    return str(item.get("titel") or item.get("title") or "").strip()


def _price(item: dict):
    for key in ("pris", "price", "current_price"):
        value = item.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return None


def _identity_key(item: dict) -> str:
    for key in ("tradera_item_id", "id", "item_id", "lank", "url", "link"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return _text(item).casefold()


def _priority_seed(item: dict) -> tuple:
    """Cheap deterministic pre-sort before the expensive fast analyser runs."""
    title = _text(item).casefold()
    collector = collector_signals(item)
    card_tokens = (
        "upper deck", "topps", "panini", "pinnacle", "opc", "o-pee-chee",
        "score", "donruss", "fleer", "select", "prizm", "chrome", "finest",
        "young guns", "rookie", "rc", "auto", "autograph", "patch", "relic",
        "#", "/25", "/50", "/99", "/100", "/199",
    )
    signal = sum(1 for token in card_tokens if token in title)
    price = _price(item)
    return (-int(collector.get("score") or 0), -signal, price if price is not None else 10**12, title)


def _num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _quick_score(result: dict) -> float:
    """Rank research priority, not economic value.

    Exact identity and actual SOLD evidence dominate. Collector title signals
    only help research ordering; they cannot create valuation or BUY evidence.
    """
    identity = _num(result.get("exact_identity_gate_score"))
    sold = int(_num(result.get("sold_comparable_count") or result.get("sold_comps")))
    valuation = _num(result.get("valuation_confidence_score"))
    rank = _num(result.get("rank_score"))
    edge = _num(result.get("market_edge_score"))
    decision = str(result.get("beslut") or result.get("decision") or "").upper()
    verified = bool(result.get("exact_identity_gate_supports_exact_comp_search"))
    collector = collector_signals(result)
    collector_score = _num(collector.get("score"))

    score = (
        min(identity, 100) * 0.34
        + min(valuation, 100) * 0.18
        + min(rank, 100) * 0.18
        + min(edge, 100) * 0.14
        + min(sold, 5) * 4.0
        + (8.0 if verified else 0.0)
        + (8.0 if decision.startswith("KÖP") else 0.0)
        + min(collector_score, 40) * 0.35
    )
    return round(max(0.0, min(100.0, score)), 1)


def _label(result: dict, score: float) -> tuple[str, str]:
    sold = int(_num(result.get("sold_comparable_count") or result.get("sold_comps")))
    verified = bool(result.get("exact_identity_gate_supports_exact_comp_search"))
    decision = str(result.get("beslut") or result.get("decision") or "").upper()
    collector = collector_signals(result)
    names = collector.get("signals") or []

    if decision.startswith("KÖP") and verified and sold >= 1:
        return "STARK KANDIDAT", "Fastanalysen hittar både köpsignal, sökbar identitet och SOLD-underlag. Kör full analys innan köp."
    if verified and sold >= 1:
        return "ANALYSERA NÄSTA", "Exakt identitet och SOLD-underlag finns. Full analys kan avgöra om samfrakten skapar ett riktigt fynd."
    if names and score >= 48:
        return "VÄRD ATT GRANSKA", "Annonsen har kortspecifika värdedrivare som motiverar djupare kontroll, men marknadsbevis saknas ännu."
    if score >= 48:
        return "VÄRD ATT GRANSKA", "Strukturen ser intressant ut, men identitet eller marknadsbevis är ännu för tunt."
    return "LÅG PRIORITET", "Fastanalysen hittar ännu inte tillräckligt stöd för att prioritera kortet."


def quick_analyze_seller_inventory(
    anchor: dict,
    items: Iterable[dict] | None,
    *,
    analyze_fn: Callable,
    sport: str = "hockey",
    strategy_mode: str = "quick_flip",
    limit: int = 20,
    shortlist: int = 5,
) -> dict:
    """Fast-analyse a capped seller inventory and return a research shortlist."""
    anchor_key = _identity_key(anchor or {})
    unique = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        prepared_item = apply_seller_metadata(item)
        key = _identity_key(prepared_item)
        if not key or key == anchor_key:
            continue
        unique[key] = dict(prepared_item)

    candidates = sorted(unique.values(), key=_priority_seed)[: max(1, int(limit))]
    rows = []
    failed = 0
    for raw in candidates:
        prepared = apply_seller_metadata(raw)
        if not prepared.get("source_category"):
            prepared["source_category"] = "Hockey - NHL" if sport == "hockey" else "Fotboll"
        try:
            result = analyze_fn(
                prepared,
                mode="fast",
                strategy_mode=strategy_mode,
                sport=sport,
            )
        except Exception:
            failed += 1
            continue
        merged = dict(prepared)
        if isinstance(result, dict):
            merged.update(result)
        merged = apply_seller_metadata(merged, prepared)
        collector = collector_signals(merged)
        score = _quick_score(merged)
        label, reason = _label(merged, score)
        rows.append({
            "title": _text(merged) or "Kortannons",
            "price": _price(merged),
            "url": merged.get("lank") or merged.get("url") or merged.get("link"),
            "decision": merged.get("beslut") or merged.get("decision") or "SKIP",
            "quick_score": score,
            "label": label,
            "reason": reason,
            "identity_ok": bool(merged.get("exact_identity_gate_supports_exact_comp_search")),
            "identity_score": _num(merged.get("exact_identity_gate_score")),
            "sold_comps": int(_num(merged.get("sold_comparable_count") or merged.get("sold_comps"))),
            "valuation_confidence": _num(merged.get("valuation_confidence_score")),
            "market_edge": _num(merged.get("market_edge_score")),
            "collector_signal_score": int(collector.get("score") or 0),
            "collector_signals": list(collector.get("signals") or []),
            "seller_alias": seller_alias(merged),
            "seller_id": seller_id(merged),
            "seller_url": seller_url(merged),
            "source_item": merged,
        })

    rows.sort(key=lambda row: (
        0 if str(row.get("decision") or "").upper().startswith("KÖP") else 1,
        0 if row.get("identity_ok") and row.get("sold_comps", 0) > 0 else 1,
        -float(row.get("quick_score") or 0),
        -int(row.get("collector_signal_score") or 0),
        row.get("price") if row.get("price") is not None else 10**12,
    ))
    shortlist_rows = rows[: max(1, min(int(shortlist), 5))]
    return {
        "status": "READY" if rows else "NO_RESULTS",
        "analysed_count": len(rows),
        "failed_count": failed,
        "rows": rows,
        "shortlist": shortlist_rows,
        "note": "Snabbanalys prioriterar vad som bör fullanalyseras. Collector-signaler är researchprioritering, inte värdering eller KÖP-bevis.",
    }
