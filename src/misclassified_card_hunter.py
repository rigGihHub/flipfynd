from __future__ import annotations

import re
from typing import Any


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("®", "").split())


def _signal_terms(signals: list[dict] | None) -> list[str]:
    terms: list[str] = []
    for signal in signals or []:
        for key in ("label", "program_family"):
            value = _norm(signal.get(key))
            if value and len(value) >= 4:
                terms.append(value)
    return list(dict.fromkeys(terms))


def build_misclassified_card_signal(
    *,
    item: dict | None,
    features: dict | None,
    knowledge_signals: list[dict] | None,
    valuable_card_knowledge: dict | None,
    listing_quality: dict | None,
    hidden_find: dict | None,
    valuation_confidence_score: int | float | None,
    sold_comparable_count: int | None,
    total_cost: int | float | None,
    expected_resale: int | float | None,
    evidence_fusion: dict | None = None,
) -> dict[str, Any]:
    """Find potentially misclassified premium/chase cards without inventing value.

    This is a discovery layer. It can reuse an already-established price gap only
    when sold-comparable evidence and valuation confidence are strong enough. It
    never creates card attributes, value, ROI, max bid or a buy decision.
    """
    item = item or {}
    features = features or {}
    signals = [dict(s) for s in (knowledge_signals or []) if isinstance(s, dict)]
    valuable = valuable_card_knowledge or {}
    listing_quality = listing_quality or {}
    hidden_find = hidden_find or {}
    evidence_fusion = evidence_fusion or {}

    tags = list(valuable.get("tags") or [])
    target_tags = [
        tag for tag in tags
        if tag in {
            "1/1", "Mycket låg numrering", "Låg numrering", "Numrerad parallel",
            "SSP / case hit", "Autograf", "Relic / patch", "RPA / rookie patch auto",
            "Rookie autograph",
        }
    ]
    if not signals or not target_tags:
        return {
            "matched": False, "score": 0, "candidate": False,
            "label": "Ingen missklassificeringssignal", "price_gap_supported": False,
            "reasons": [], "cautions": [], "safe_for_valuation": False,
        }

    title = _norm(item.get("titel"))
    raw = _norm(item.get("raw_text"))
    score = 0
    discovery = 0
    reasons: list[str] = []
    cautions: list[str] = []

    # Known product/program/variant terminology visible in richer listing evidence
    # but omitted from the public title is the strongest discovery signal.
    terms = _signal_terms(signals)
    missing_terms = [term for term in terms if term in raw and term not in title]
    if missing_terms:
        score += min(34, 18 + 6 * len(missing_terms))
        discovery += 1
        reasons.append("Känd kort-/variantterminologi finns i annonsinformationen men saknas i titeln: " + ", ".join(missing_terms[:3]) + ".")

    enriched = set(features.get("identity_enriched_fields") or [])
    important = enriched.intersection({"set_name", "card_number", "parallel", "serial_number", "autograph", "patch", "season", "year"})
    if important:
        score += min(24, 6 * len(important))
        discovery += 1
        reasons.append("Viktig kortidentitet finns utanför titeln: " + ", ".join(sorted(important)) + ".")

    # Premium/chase trait is documented by knowledge signals, but this remains an
    # identification priority rather than a price premium.
    if "1/1" in target_tags:
        score += 18
        reasons.append("Kunskapsbanken matchar en dokumenterad 1/1-struktur.")
    elif any(t in target_tags for t in ("Mycket låg numrering", "Låg numrering")):
        score += 14
        reasons.append("Kunskapsbanken matchar en dokumenterat lågnumrerad struktur.")
    elif "SSP / case hit" in target_tags:
        score += 14
        reasons.append("Kunskapsbanken matchar SSP/case-hit-struktur.")
    elif any(t in target_tags for t in ("Autograf", "Relic / patch", "RPA / rookie patch auto", "Rookie autograph")):
        score += 10

    tokens = re.findall(r"[a-z0-9åäö]+", title)
    generic = {"kort", "card", "hockey", "fotboll", "football", "nhl", "auto", "autograph", "patch", "rookie", "rc"}
    meaningful = [x for x in tokens if x not in generic]
    if len(tokens) <= 5 or len(meaningful) <= 3:
        score += 10
        discovery += 1
        reasons.append("Titeln är kort/generisk och kan dölja den exakta varianten i sökresultat.")

    quality = int(listing_quality.get("score", 0) or 0)
    if quality < 55:
        score += 8
        discovery += 1
        reasons.append(f"Annonskvaliteten är låg ({quality}/100).")
    hidden = int(hidden_find.get("score", 0) or 0)
    if hidden >= 55:
        score += 10
        discovery += 1
        reasons.append(f"Dold-fynd-signalen är hög ({hidden}/100).")

    sold = max(0, int(sold_comparable_count or 0))
    valuation_conf = max(0, min(100, int(round(float(valuation_confidence_score or 0)))))
    try:
        cost = float(total_cost or 0)
        expected = float(expected_resale or 0)
    except (TypeError, ValueError):
        cost, expected = 0.0, 0.0
    price_gap_supported = bool(sold >= 2 and valuation_conf >= 60 and cost > 0 and expected >= cost * 1.25)
    if price_gap_supported:
        score += 16
        reasons.append("Befintlig värderingsanalys visar ett comp-stött prisgap.")
    else:
        cautions.append("Discovery-signalen bevisar inte felprissättning; tillräckligt comp-stött prisgap saknas.")

    conflicts = list(features.get("identity_conflicts") or [])
    identity = int(features.get("identity_confidence_score", 0) or 0)
    if conflicts:
        score = min(score, 44)
        cautions.append("Identitetskonflikt finns mellan titel och övrig annonsinformation.")
    elif identity < 45:
        score = min(score, 54)
        cautions.append("Kortidentiteten är osäker; verifiera bild, kortnummer och variant.")
    if evidence_fusion.get("has_conflict"):
        score = min(score, 42)
        cautions.append("Evidence Fusion visar konflikt mellan titel, detaljbeskrivning eller bildbevis; stark hunter-signal spärras.")
    elif int(evidence_fusion.get("score", 0) or 0) >= 70 and len(evidence_fusion.get("corroborated_fields") or []) >= 2:
        reasons.append("Flera oberoende annonskällor stödjer samma kortidentitet.")

    if features.get("is_lot"):
        score = min(score, 49)
        cautions.append("Lot/paket-annons: enskilt kort kan inte isoleras säkert.")

    score = int(max(0, min(100, round(score))))
    candidate = bool(discovery >= 1 and score >= 50)
    if price_gap_supported and score >= 75:
        label = "Prisgap + möjlig missklassificering"
    elif score >= 75:
        label = "Stark missklassificeringskandidat"
    elif candidate:
        label = "Möjlig missklassificerad variant"
    else:
        label = "Ingen tydlig missklassificerings-edge"

    next_action = None
    if candidate:
        next_action = "Verifiera exakt set/program, variant, kortnummer och numrering mot bilder och exact sold comps innan köp/bud."

    return {
        "matched": True,
        "score": score,
        "candidate": candidate,
        "label": label,
        "price_gap_supported": price_gap_supported,
        "target_tags": target_tags[:8],
        "discovery_signal_count": discovery,
        "reasons": reasons[:7],
        "cautions": list(dict.fromkeys(cautions))[:6],
        "next_action": next_action,
        "safe_for_valuation": False,
        "note": (
            "Misclassified Card Hunter letar efter underbeskrivna paralleller, autos, patchar, SSP/case hits, "
            "lågnumrerade kort och 1/1. Den får inte skapa kortattribut, värde, ROI, maxbud eller köpbeslut."
        ),
    }
