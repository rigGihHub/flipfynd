"""Decision-first summary for FlipFynd's real-outcome calibration.

This module only summarizes evidence already present in Flip Journal and the
existing calibration/miss-analysis engines. It never changes model weights and
never turns descriptive history into causal claims.
"""
from __future__ import annotations

from typing import Any, Iterable

from src.outcome_calibration import build_outcome_calibration
from src.calibration_miss_analysis import build_miss_analysis
from src.outcome_review import normalize_review_reasons


def _sold_rows(entries: Iterable[dict]) -> list[dict]:
    return [row for row in entries if row.get("status") == "sålt" and row.get("actual_net_profit") is not None]


def build_calibration_dashboard(entries: Iterable[dict]) -> dict[str, Any]:
    rows = list(entries)
    sold = _sold_rows(rows)
    calibration = build_outcome_calibration(rows)
    misses = build_miss_analysis(rows)

    reviewed = [
        row for row in sold
        if normalize_review_reasons(row.get("outcome_review_reasons"))
        or str(row.get("outcome_review_note") or "").strip()
    ]
    review_rate = round(len(reviewed) / len(sold) * 100, 1) if sold else None

    sample = calibration["overall"]["sample"]
    if not sold:
        readiness = "empty"
        headline = "Ingen verklig kalibreringsdata ännu"
        next_action = "Logga köp och avsluta verkliga affärer i Flip Journal."
    elif not sample["supports_description"]:
        readiness = "collecting"
        headline = "Samlar underlag"
        next_action = f"Fortsätt logga avslut. {sample['message']}"
    elif not sample["supports_tendency"]:
        readiness = "descriptive"
        headline = "Grundläggande utfallsbild finns"
        next_action = "Fortsätt samla avslut innan signaler jämförs som historiska tendenser."
    elif not sample["supports_adjustment_review"]:
        readiness = "tendency"
        headline = "Historiska tendenser kan granskas"
        next_action = "Använd tendenserna som granskningsunderlag, inte som automatiska modelländringar."
    else:
        readiness = "review_ready"
        headline = "Tillräckligt underlag för manuell modellgranskning"
        next_action = "Granska återkommande styrkor och missar innan någon modellvikt ändras."

    best = calibration.get("best_tendency")
    primary_miss = misses.get("primary_pattern")

    attention: list[dict[str, str]] = []
    if primary_miss:
        attention.append({
            "kind": "miss",
            "title": primary_miss["label"],
            "message": f"Återkommer i {primary_miss['count']} avslut. Granska orsaken innan modellen justeras.",
        })
    if sold and review_rate is not None and review_rate < 50:
        attention.append({
            "kind": "review",
            "title": "Få avslut har Outcome Review",
            "message": f"{len(reviewed)} av {len(sold)} avslut har manuell utfallsgranskning. Fler verifierade orsaker förbättrar felsökningen.",
        })

    return {
        "readiness": readiness,
        "headline": headline,
        "next_action": next_action,
        "sold_count": len(sold),
        "reviewed_count": len(reviewed),
        "review_rate_pct": review_rate,
        "overall": calibration["overall"],
        "groups": calibration["groups"],
        "best_tendency": best,
        "worst_tendency": calibration.get("worst_tendency"),
        "miss_analysis": misses,
        "attention": attention,
        "automatic_weight_changes": False,
        "note": (
            "Dashboarden sammanfattar bara verkliga journalutfall. Den visar historiska samband, "
            "inte bevisade orsaker, och ändrar aldrig modellvikter automatiskt."
        ),
    }
