"""Fuse visual findings, listing text, observed records and checklist structure.

This resolver answers a collector-facing question: "what exact card is this most
likely to be?". It is intentionally conservative. A high-ranked candidate is
still a hypothesis unless independent structured evidence corroborates the
identity. Checklist structure can strengthen or weaken a candidate but does not
on its own verify player/card-number authenticity or create a valuation.
"""
from __future__ import annotations

from typing import Any, Iterable

from src.visual_identity import build_visual_card_candidates
from src.visual_checklist_match import match_visual_to_checklist_knowledge


def _candidate_key(c: dict[str, Any]) -> tuple:
    f = c.get("identity_fields") or {}
    return tuple(str(f.get(k) or "").casefold().strip() for k in (
        "player_name", "set_name", "season", "card_number", "parallel", "serial_denominator"
    ))


def resolve_visual_exact_identity(
    findings: dict,
    *,
    listing_title: str = "",
    listing_raw_text: str = "",
    observed_records: Iterable[dict] | None = None,
    sport: str | None = None,
    max_candidates: int = 3,
) -> dict[str, Any]:
    """Return a ranked exact-card hypothesis with alternatives and blockers."""
    identity = build_visual_card_candidates(
        findings or {},
        listing_title=listing_title,
        listing_raw_text=listing_raw_text,
        observed_records=observed_records,
        max_candidates=max_candidates,
    )
    checklist = match_visual_to_checklist_knowledge(findings or {}, sport=sport)

    checklist_conflicts = [m for m in checklist.get("matches", []) if m.get("conflict")]
    checklist_support = [m for m in checklist.get("matches", []) if not m.get("conflict") and m.get("match_score", 0) >= 70]

    ranked: list[dict[str, Any]] = []
    seen = set()
    for candidate in identity.get("candidates", []):
        key = _candidate_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        base = float(candidate.get("match_score") or 0)
        reasons = list(candidate.get("evidence") or [])
        cautions: list[str] = []
        structural_score = 0.0

        if checklist_conflicts:
            structural_score -= 24
            cautions.append("Bilddetaljer krockar med minst en dokumenterad variant-/print-run-struktur")
        elif checklist_support:
            best = max(checklist_support, key=lambda m: float(m.get("match_score") or 0))
            structural_score += min(16.0, float(best.get("match_score") or 0) * 0.16)
            reasons.append("checklist/variantstruktur stöder hypotesen")

        fields = candidate.get("identity_fields") or {}
        completeness_fields = ["player_name", "set_name", "season", "card_number", "parallel"]
        completeness = sum(1 for k in completeness_fields if fields.get(k)) / len(completeness_fields)
        completeness_bonus = completeness * 10
        if not fields.get("card_number"):
            cautions.append("Kortnummer saknas eller är osäkert")
        if not fields.get("parallel") and (findings or {}).get("parallel_or_variant"):
            cautions.append("Variant/parallel är inte säkert knuten till kandidaten")

        verified = bool(candidate.get("verified_identity"))
        verification_bonus = 12 if verified else 0
        score = max(0, min(100, round(base * 0.72 + completeness_bonus + structural_score + verification_bonus)))

        if verified and not checklist_conflicts and score >= 80:
            status = "Mest sannolikt exakt detta kort"
        elif score >= 65 and not checklist_conflicts:
            status = "Starkaste kortkandidaten"
        elif score >= 45:
            status = "Möjlig kortkandidat"
        else:
            status = "Svag kortkandidat"

        ranked.append({
            **candidate,
            "combined_score": score,
            "status": status,
            "reasons": reasons[:6],
            "cautions": cautions[:5],
            "checklist_support_count": len(checklist_support),
            "checklist_conflict_count": len(checklist_conflicts),
            "field_completeness": round(completeness, 2),
        })

    ranked.sort(key=lambda c: (bool(c.get("verified_identity")), float(c.get("combined_score") or 0)), reverse=True)
    ranked = ranked[:max(1, int(max_candidates))]

    blockers = list(identity.get("blockers") or [])
    if checklist_conflicts:
        blockers.append("Checklist-/variantkonflikt måste lösas innan exakt identitet kan godtas")
    top = ranked[0] if ranked else None
    exact_ready = bool(top and top.get("verified_identity") and not checklist_conflicts and top.get("combined_score", 0) >= 80)

    if exact_ready:
        status = "Mest sannolikt exakt kort identifierat"
    elif top:
        status = "Bästa kortkandidat hittad – verifiering återstår"
    else:
        status = "Kan inte identifiera exakt kort ännu"

    next_actions: list[str] = []
    if top:
        fields = top.get("identity_fields") or {}
        if not fields.get("card_number"):
            next_actions.append("Läs kortnummer på baksida eller checklistnummer i närbild")
        if not fields.get("set_name"):
            next_actions.append("Identifiera set/produkt via logo, copyrighttext eller baksida")
        if not fields.get("season"):
            next_actions.append("Bekräfta år/säsong från kortets baksida eller officiell checklist")
        if not top.get("verified_identity"):
            next_actions.append("Bekräfta mot oberoende strukturerad källa eller verifierad såld comp")
    if checklist_conflicts:
        next_actions.insert(0, "Lös motsägelsen mellan synlig variant/print run och dokumenterad checkliststruktur")

    return {
        "status": status,
        "best_candidate": top,
        "alternatives": ranked[1:],
        "candidates": ranked,
        "blockers": blockers[:5],
        "next_actions": next_actions[:4],
        "exact_identity_ready": exact_ready,
        "can_search_exact_comps": exact_ready,
        "safe_for_valuation": False,
        "checklist_status": checklist.get("status"),
        "note": "Detta är en identitetsresolver, inte en värderingsmotor. Bild + checkliststruktur får föreslå exakt kort men inte skapa marknadsvärde eller KÖP utan separat marknadsevidens.",
    }
