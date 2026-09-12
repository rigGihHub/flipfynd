"""Evidence grading for checklist, case-hit and short-print claims.

A rarity label is not a price. This module separates objective scarcity evidence
(serial numbering / published pack odds) from manufacturer chase language and
unsupported marketplace wording such as "SSP" or "case hit".
"""
from __future__ import annotations

import re
from typing import Any

from src.pull_frequency_context import contextualize_pull_frequency


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _odds_strength(value: Any) -> int | None:
    """Return denominator from common odds text such as '1:144 Hobby'."""
    text = str(value or "")
    match = re.search(r"1\s*[:/]\s*([0-9][0-9,]*)", text)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def grade_rarity_evidence(signals: list[dict] | None) -> dict[str, Any]:
    rows = [dict(row) for row in (signals or []) if isinstance(row, dict)]
    evidence: list[dict[str, Any]] = []
    warnings: list[str] = []

    for row in rows:
        label = str(row.get("label") or row.get("program_family") or "Känd kortstruktur")
        category = _norm(row.get("category"))
        rarity = _norm(row.get("rarity_signal"))
        source_id = str(row.get("source_id") or "").strip()
        print_run = row.get("print_run")
        odds = row.get("pull_odds") or row.get("published_odds")
        odds_den = _odds_strength(odds)
        frequency = contextualize_pull_frequency(row)

        run: int | None = None
        try:
            if print_run not in (None, ""):
                run = int(print_run)
        except (TypeError, ValueError):
            run = None

        if run and run > 0:
            kind = "serial_numbered"
            status = f"Verifierad serienumrering /{run}"
            confidence = 100 if source_id else 78
            objective = True
        elif odds_den:
            kind = "published_odds"
            status = f"Publicerade packodds {odds}"
            confidence = 96 if source_id else 72
            objective = True
        elif "case hit" in category or "case_hit" in str(row.get("category") or "").casefold():
            kind = "case_hit_claim"
            if source_id:
                status = "Källstyrd case-hit/case-pull-signal"
                confidence = 88
            else:
                status = "Case-hit-term utan kopplad källa"
                confidence = 42
                warnings.append(f"{label}: 'case hit' är inte källverifierat i kunskapsbasen.")
            objective = False
        elif "ssp" in category or "ssp" in rarity or "short print" in rarity or "short_print" in str(row.get("rarity_signal") or "").casefold():
            kind = "short_print_claim"
            if source_id:
                status = "Källstyrd SSP/short-print-signal"
                confidence = 84
            else:
                status = "SSP/short-print-term utan kopplad källa"
                confidence = 40
                warnings.append(f"{label}: SSP/short-print är inte källverifierat i kunskapsbasen.")
            objective = False
        elif "chase" in category or "chase" in rarity or "chase" in _norm(row.get("program_family")):
            kind = "manufacturer_chase"
            if source_id:
                status = "Officiellt chase-program; exakt sällsynthet ej kvantifierad"
                confidence = 74
            else:
                status = "Chase-term utan kopplad källa"
                confidence = 38
            objective = False
        else:
            continue

        evidence.append({
            "label": label,
            "kind": kind,
            "status": status,
            "confidence_score": confidence,
            "objective_scarcity": objective,
            "print_run": run,
            "pull_odds": odds,
            "frequency_band": frequency.get("frequency_band"),
            "frequency_label": frequency.get("frequency_label"),
            "packs_per_hit": frequency.get("packs_per_hit"),
            "boxes_per_hit": frequency.get("boxes_per_hit"),
            "cases_per_hit": frequency.get("cases_per_hit"),
            "product_configuration_complete": frequency.get("configuration_complete"),
            "source_id": source_id or None,
            "product_family": row.get("product_family"),
            "importance_reason": row.get("importance_reason"),
            "collectible_hierarchy_tier": row.get("collectible_hierarchy_tier"),
            "collectible_hierarchy_rank": row.get("collectible_hierarchy_rank"),
            "collectible_hierarchy_label": row.get("collectible_hierarchy_label"),
        })

    evidence.sort(
        key=lambda x: (
            bool(x.get("objective_scarcity")),
            int(x.get("confidence_score") or 0),
            -int(x.get("print_run") or 10**9),
        ),
        reverse=True,
    )

    objective = [e for e in evidence if e.get("objective_scarcity")]
    sourced = [e for e in evidence if e.get("source_id")]
    unsupported = [e for e in evidence if not e.get("source_id") and e.get("kind") in {"case_hit_claim", "short_print_claim"}]

    if objective:
        status = "Objektiv raritet verifierad"
        score = max(int(e.get("confidence_score") or 0) for e in objective)
    elif sourced:
        status = "Källstyrd chase/raritetssignal – exakt knapphet ej bevisad"
        score = max(int(e.get("confidence_score") or 0) for e in sourced)
    elif unsupported:
        status = "Raritetsord upptäckt men inte verifierat"
        score = max(int(e.get("confidence_score") or 0) for e in unsupported)
    else:
        status = "Ingen särskild raritet verifierad"
        score = 0

    return {
        "status": status,
        "confidence_score": score,
        "evidence": evidence[:8],
        "objective_evidence_count": len(objective),
        "source_backed_count": len(sourced),
        "unsupported_claim_count": len(unsupported),
        "warnings": list(dict.fromkeys(warnings))[:6],
        "exact_rarity_verified": bool(objective),
        "safe_for_valuation": False,
        "note": (
            "Rarity Evidence skiljer verifierad serienumrering/packodds från chase-, SSP- och case-hit-termer. "
            "Ingen raritet får ensam skapa marknadsvärde eller KÖP-signal."
        ),
    }
