"""Plain-language presentation helpers for FlipFynd novice views.

Presentation only: never changes valuation, ranking, buy decisions or max prices.
"""
from __future__ import annotations


def sold_evidence_text(count) -> str:
    try:
        n = max(0, int(count or 0))
    except (TypeError, ValueError):
        n = 0
    if n == 0:
        return "Saknar verifierade försäljningar"
    if n == 1:
        return "1 verifierad försäljning"
    return f"{n} verifierade försäljningar"


def identity_text(status) -> str:
    s = str(status or "").strip().upper()
    return {
        "VERIFIERAD": "Kortet är tydligt identifierat",
        "SÖKBAR": "Kortet är identifierat, men maxpris kräver mer stöd",
        "GRANSKA": "Kortet behöver identifieras säkrare",
        "LÅST": "Kortets identitet är för osäker",
    }.get(s, "Kortidentiteten är inte säkert verifierad")


def sellability_text(label=None, score=None) -> str:
    raw = str(label or "").strip().lower()
    if "mycket lätt" in raw or "lättsålt" in raw or "lätts" in raw:
        return "Lätt att sälja"
    if "svår" in raw or "trög" in raw:
        return "Svårare att sälja"
    if raw in {"normalt", "normal"}:
        return "Normal säljbarhet"
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "Säljbarhet ej verifierad"
    if value >= 68:
        return "Lätt att sälja"
    if value < 50:
        return "Svårare att sälja"
    return "Normal säljbarhet"


def compact_evidence_summary(item: dict) -> list[str]:
    item = item or {}
    parts = [identity_text(item.get("exact_identity_gate_status"))]
    parts.append(sold_evidence_text(item.get("sold_comparable_count")))
    parts.append(sellability_text(item.get("liquidity_label") or item.get("sellability_label"), item.get("liquidity_score") or item.get("sellability_score")))
    return parts
