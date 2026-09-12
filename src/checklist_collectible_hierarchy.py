"""Source-aware collectible hierarchy for checklist/chase knowledge.

This module classifies *what kind of collectible structure* a documented signal is.
It is deliberately not a pricing model: tiers can raise analysis attention and
explain hobby importance, but they must never create a price premium by themselves.
"""
from __future__ import annotations

import re
from typing import Any

from src.pull_frequency_context import contextualize_pull_frequency


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _odds_den(value: Any) -> int | None:
    m = re.search(r"1\s*[:/]\s*([0-9][0-9,]*)", str(value or ""))
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


TIERS = {
    "flagship_rookie": (2, "Flagship rookie / nyckel-rookieprogram"),
    "key_insert": (2, "Nyckelinsert / samlarprogram"),
    "numbered_parallel": (3, "Numrerad parallel"),
    "source_backed_ssp": (4, "Källstyrd SSP / ultra-rare insert"),
    "published_frequency": (2, "Publicerad frekvens – inte sällsynt i sig"),
    "published_odds_chase": (4, "Chase med publicerade odds"),
    "case_level_hit": (5, "Källstyrd case-level hit"),
    "one_of_one": (6, "1/1 / grail-struktur"),
    "manufacturer_chase": (1, "Tillverkarens chase-program; knapphet ej kvantifierad"),
    "other": (0, "Övrig dokumenterad struktur"),
}


def classify_collectible_signal(signal: dict[str, Any]) -> dict[str, Any]:
    row = signal or {}
    category = _norm(row.get("category"))
    rarity = _norm(row.get("rarity_signal"))
    label = _norm(row.get("label"))
    program = _norm(row.get("program_family"))
    source_backed = bool(str(row.get("source_id") or "").strip())
    run = row.get("print_run")
    try:
        run_i = int(run) if run not in (None, "") else None
    except (TypeError, ValueError):
        run_i = None
    odds = row.get("pull_odds") or row.get("published_odds")
    odds_i = _odds_den(odds)
    frequency = contextualize_pull_frequency(row)

    if run_i == 1 or "one of one" in rarity or "1 1" in rarity:
        key = "one_of_one"
        reason = "Dokumenterad 1/1-struktur."
    elif source_backed and ("case hit" in category or "case level" in rarity or "case pull" in rarity):
        key = "case_level_hit"
        reason = "Tillverkarkälla beskriver strukturen på case-level/case-pull-nivå."
    elif odds_i:
        if odds_i <= 12:
            key = "published_frequency"
            reason = f"Tillverkaren publicerar odds {odds}; frekvensen är dokumenterad men är inte i sig ett starkt raritetsbevis."
        else:
            key = "published_odds_chase"
            reason = f"Tillverkaren publicerar odds {odds}; det ger objektivt frekvensstöd."
    elif run_i and run_i > 1:
        key = "numbered_parallel"
        reason = f"Dokumenterad serienumrering /{run_i}."
    elif source_backed and (category == "ssp insert" or "ssp" in rarity or "ultra rare" in rarity):
        key = "source_backed_ssp"
        reason = "SSP/ultra-rare-beteckningen är kopplad till en tillverkarkälla."
    elif "rookie" in category or "rookie" in rarity or "young guns" in label or "future watch" in label:
        key = "flagship_rookie"
        reason = "Dokumenterat rookieprogram; hobbyviktigt men inte automatiskt sällsynt."
    elif source_backed and ("chase" in category or "chase" in rarity or "chase" in program):
        key = "manufacturer_chase"
        reason = "Tillverkaren lyfter programmet som chase, men exakt knapphet är inte kvantifierad."
    elif category in {"insert", "key insert", "memorabilia", "autograph program", "autograph_program"}:
        key = "key_insert"
        reason = "Dokumenterat insert-/samlarprogram."
    else:
        key = "other"
        reason = "Dokumenterad struktur utan särskild verifierad raritetsnivå."

    rank, label_text = TIERS[key]
    return {
        "tier": key,
        "rank": rank,
        "label": label_text,
        "reason": reason,
        "source_backed": source_backed,
        "objective_scarcity": bool(run_i or (odds_i and odds_i > 12)),
        "published_frequency": odds_i,
        "print_run": run_i,
        "pull_odds": odds,
        "frequency_band": frequency.get("frequency_band"),
        "frequency_label": frequency.get("frequency_label"),
        "packs_per_hit": frequency.get("packs_per_hit"),
        "boxes_per_hit": frequency.get("boxes_per_hit"),
        "cases_per_hit": frequency.get("cases_per_hit"),
        "product_configuration_complete": frequency.get("configuration_complete"),
        "safe_for_valuation": False,
    }


def summarize_collectible_hierarchy(signals: list[dict] | None) -> dict[str, Any]:
    rows = [dict(s) for s in (signals or []) if isinstance(s, dict)]
    classified = []
    for row in rows:
        c = classify_collectible_signal(row)
        c["signal_label"] = row.get("label")
        c["product_family"] = row.get("product_family")
        classified.append(c)
    classified.sort(key=lambda r: (int(r.get("rank") or 0), bool(r.get("objective_scarcity"))), reverse=True)
    top = classified[0] if classified else None
    return {
        "top_tier": top.get("tier") if top else None,
        "top_rank": int(top.get("rank") or 0) if top else 0,
        "top_label": top.get("label") if top else "Ingen dokumenterad samlarhierarki",
        "entries": classified[:8],
        "note": "Hierarkin beskriver checklist-/hobbystruktur och får inte ensam skapa marknadsvärde eller KÖP-signal.",
    }
