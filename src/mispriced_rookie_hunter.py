from __future__ import annotations

import re
from typing import Any


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("®", "").split())


def _program_terms(rookie_importance: dict | None) -> list[str]:
    rule = (rookie_importance or {}).get("program_rule") or {}
    return [_norm(x) for x in (rule.get("patterns") or []) if _norm(x)]


def build_mispriced_rookie_signal(
    *,
    item: dict | None,
    features: dict | None,
    rookie_importance: dict | None,
    listing_quality: dict | None,
    hidden_find: dict | None,
    player_market_score: int | float | None,
    valuation_confidence_score: int | float | None,
    sold_comparable_count: int | None,
    total_cost: int | float | None,
    expected_resale: int | float | None,
    evidence_fusion: dict | None = None,
) -> dict[str, Any]:
    """Find rookie listings that may be under-described or misclassified.

    The signal may *reuse* an already-calculated price gap when market evidence is
    strong enough, but it never creates a market value, buy recommendation, ROI or
    max bid. Its main job is discovery: find listings whose title understates the
    rookie/program/variant identity present elsewhere in the listing evidence.
    """
    item = item or {}
    features = features or {}
    rookie_importance = rookie_importance or {}
    listing_quality = listing_quality or {}
    hidden_find = hidden_find or {}
    evidence_fusion = evidence_fusion or {}

    if not rookie_importance.get("matched"):
        return {
            "matched": False,
            "score": 0,
            "label": "Ingen rookie-signal",
            "candidate": False,
            "price_gap_supported": False,
            "reasons": [],
            "cautions": [],
            "safe_for_valuation": False,
        }

    title = _norm(item.get("titel"))
    raw = _norm(item.get("raw_text"))
    score = 0
    reasons: list[str] = []
    cautions: list[str] = []
    discovery_signals = 0

    # 1) A named rookie program is present in the richer listing evidence but absent
    # from the public title. This is the strongest "other buyers may miss it" signal.
    program_terms = _program_terms(rookie_importance)
    program_in_title = any(term in title for term in program_terms)
    program_in_raw = any(term in raw for term in program_terms)
    if program_terms and not program_in_title and program_in_raw:
        score += 30
        discovery_signals += 1
        reasons.append("Rookieprogrammet syns i annonsinformationen men saknas i titeln.")
    elif program_terms and program_in_title:
        score -= 10

    enriched = set(features.get("identity_enriched_fields") or [])
    important_enriched = enriched.intersection(
        {"set_name", "card_number", "parallel", "rookie_variant", "serial_number", "season", "year"}
    )
    if important_enriched:
        add = min(24, 6 * len(important_enriched))
        score += add
        discovery_signals += 1
        reasons.append(
            "Viktig kortidentitet finns utanför titeln: " + ", ".join(sorted(important_enriched)) + "."
        )

    # 2) Generic/weak listing titles are discovery opportunities, not value evidence.
    tokens = re.findall(r"[a-z0-9åäö]+", title)
    generic_words = {"rookie", "rc", "kort", "card", "hockey", "fotboll", "football", "nhl"}
    non_generic = [t for t in tokens if t not in generic_words]
    if len(tokens) <= 5 or len(non_generic) <= 3:
        score += 12
        discovery_signals += 1
        reasons.append("Titeln är kort/generisk och kan vara svag i sökresultat.")

    quality = int(listing_quality.get("score", 0) or 0)
    if quality < 55:
        score += 10
        discovery_signals += 1
        reasons.append(f"Annonskvaliteten är låg ({quality}/100), vilket ökar risken att identiteten är underbeskriven.")
    elif quality < 70:
        score += 5

    hidden = int(hidden_find.get("score", 0) or 0)
    if hidden >= 55:
        score += 12
        discovery_signals += 1
        reasons.append(f"Dold-fynd-signalen är hög ({hidden}/100).")
    elif hidden >= 35:
        score += 6

    player_score = max(0, min(100, int(round(float(player_market_score or 0)))))
    importance = max(0, min(100, int(rookie_importance.get("importance_score", 0) or 0)))
    if player_score >= 85:
        score += 10
        reasons.append(f"Spelarefterfrågan är hög ({player_score}/100).")
    elif player_score >= 70:
        score += 6
    if importance >= 88:
        score += 10
        reasons.append(f"Rookieprogrammet har hög verifieringsvikt ({importance}/100).")
    elif importance >= 76:
        score += 6

    # 3) Existing price analysis may confirm a gap, but only with meaningful sold
    # evidence and valuation confidence. We do not calculate a new value here.
    valuation_conf = max(0, min(100, int(round(float(valuation_confidence_score or 0)))))
    sold = max(0, int(sold_comparable_count or 0))
    try:
        cost = float(total_cost or 0)
        expected = float(expected_resale or 0)
    except (TypeError, ValueError):
        cost, expected = 0.0, 0.0
    price_gap_supported = bool(
        sold >= 2
        and valuation_conf >= 60
        and cost > 0
        and expected >= cost * 1.25
    )
    if price_gap_supported:
        score += 18
        reasons.append(
            "Befintlig värderingsanalys visar även ett prisgap med minst två sold comps och tillräcklig värderingssäkerhet."
        )
    elif sold < 2 or valuation_conf < 60:
        cautions.append("Prisgapet är inte tillräckligt comp-verifierat för att kalla annonsen felprissatt.")

    conflicts = list(features.get("identity_conflicts") or [])
    identity_score = int(features.get("identity_confidence_score", 0) or 0)
    if conflicts:
        score = min(score, 44)
        cautions.append("Identitetskonflikt finns mellan titel och övrig annonsinformation.")
    elif identity_score < 45:
        score = min(score, 54)
        cautions.append("Kortidentiteten är osäker; verifiera bild/kortnummer innan du agerar.")

    if evidence_fusion.get("has_conflict"):
        score = min(score, 42)
        cautions.append("Evidence Fusion visar konflikt mellan titel, detaljbeskrivning eller bildbevis; stark hunter-signal spärras.")
    elif int(evidence_fusion.get("score", 0) or 0) >= 70 and len(evidence_fusion.get("corroborated_fields") or []) >= 2:
        reasons.append("Flera oberoende annonskällor stödjer samma kortidentitet.")

    if features.get("is_lot"):
        score = min(score, 49)
        cautions.append("Lot/paket-annons: en enskild rookies identitet och pris kan inte isoleras säkert.")

    score = int(max(0, min(100, round(score))))
    candidate = bool(discovery_signals >= 1 and score >= 50)

    if price_gap_supported and score >= 75:
        label = "Prisgap + underbeskriven rookie"
    elif score >= 70:
        label = "Stark underbeskriven rookie-kandidat"
    elif candidate:
        label = "Möjlig underbeskriven rookie"
    else:
        label = "Ingen tydlig rookie-edge"

    next_action = None
    if candidate:
        if price_gap_supported:
            next_action = "Verifiera exakt rookieprogram, variant och kortnummer mot sold comps innan köp/bud."
        else:
            next_action = "Öppna annonsen och verifiera bilder, kortnummer och variant; sök sedan exact sold comps."

    return {
        "matched": True,
        "score": score,
        "label": label,
        "candidate": candidate,
        "price_gap_supported": price_gap_supported,
        "discovery_signal_count": discovery_signals,
        "reasons": reasons[:7],
        "cautions": list(dict.fromkeys(cautions))[:6],
        "next_action": next_action,
        "safe_for_valuation": False,
        "note": (
            "Mispriced Rookie Hunter hittar främst underbeskrivna/missklassificerade rookieannonser. "
            "Den får inte skapa värde, ROI, maxbud eller köpbeslut. 'Felprissatt' används bara när befintlig "
            "värdering redan stöds av sold comps och tillräcklig värderingssäkerhet."
        ),
    }
