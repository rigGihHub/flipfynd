"""Collector Worth Intelligence.

Explains whether a card has a strong *collector-value profile* and why. This is
not a price model. It combines documented card structure, player demand,
identity quality, grading context and observed market evidence. Monetary value
still requires exact comparable sales.
"""
from __future__ import annotations


def _clamp(v, lo=0, hi=100):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return float(lo)


def _grade_context(features):
    features = features or {}
    company = str(features.get("grading_company") or "").upper().strip()
    grade = str(features.get("grade") or "").upper().strip()
    if not company and not grade:
        return {"recognized": False, "label": "Raw/ograderat eller okänd grade", "strength": 0, "caution": None}
    recognized = company in {"PSA", "BGS", "SGC"}
    numeric = None
    try:
        import re
        m = re.search(r"(10|9\.5|9|8\.5|8|7\.5|7|6)$", grade)
        numeric = float(m.group(1)) if m else None
    except Exception:
        numeric = None
    strength = 0
    caution = None
    if recognized and numeric is not None:
        if numeric >= 9.5:
            strength = 100
        elif numeric >= 9:
            strength = 78
        elif numeric >= 8:
            strength = 45
            caution = "Graderat kort, men graden ger inte automatiskt en stark premie."
        else:
            strength = 25
            caution = "Lägre grade kan begränsa premium; exakt kort och era-specifik marknad måste jämföras."
    elif recognized:
        strength = 35
        caution = "Graderingsbolaget känns igen men graderingsnivån kunde inte tolkas säkert."
    else:
        caution = "Okänt/ej verifierat graderingsbolag ska inte få automatisk premium."
    return {
        "recognized": recognized,
        "label": f"{company} {grade}".strip() or "Graderat",
        "strength": strength,
        "caution": caution,
    }


def build_collector_worth_profile(
    *,
    player_name,
    player_market_score,
    variant_rung,
    rookie_importance_score,
    rookie_importance_matched,
    valuable_structure_score,
    valuable_tags,
    sold_comparable_count,
    valuation_confidence_score,
    identity_confidence_score,
    liquidity_score,
    features=None,
    hierarchy_score=0,
    hierarchy_tier=None,
):
    """Return a collector-facing value-quality profile, never a price estimate."""
    features = dict(features or {})
    player = _clamp(player_market_score)
    variant = max(0, int(variant_rung or 0))
    rookie = _clamp(rookie_importance_score) if rookie_importance_matched else 0
    structure = _clamp(valuable_structure_score)
    sold = max(0, int(sold_comparable_count or 0))
    valuation_conf = _clamp(valuation_confidence_score)
    identity_conf = _clamp(identity_confidence_score)
    liquidity = _clamp(liquidity_score)
    tags = [str(t) for t in (valuable_tags or []) if t]
    grade = _grade_context(features)
    hierarchy = _clamp(hierarchy_score)

    # Structural desirability is deliberately separate from market proof.
    structure_strength = max(structure, min(100, variant * 16 + (8 if rookie >= 70 else 0)), hierarchy)
    if tags:
        structure_strength = min(100, structure_strength + min(12, len(tags) * 3))

    market_proof = min(100, sold * 18) * 0.55 + valuation_conf * 0.30 + liquidity * 0.15
    market_proof = _clamp(market_proof)

    # Collector quality profile, not market price. Strong structure without player
    # demand and market proof cannot score like a true high-quality collectible.
    score = (
        player * 0.30
        + structure_strength * 0.25
        + identity_conf * 0.15
        + market_proof * 0.20
        + grade["strength"] * 0.10
    )

    strengths = []
    cautions = []
    traps = []

    if player >= 85:
        strengths.append("Stark etablerad spelarefterfrågan")
    elif player < 55:
        cautions.append("Svag eller osäker spelarefterfrågan")

    if rookie_importance_matched and rookie >= 75:
        strengths.append("Relevant rookieprogram med hög strukturell betydelse")
    if hierarchy >= 78:
        strengths.append("Kortet ligger i en stark dokumenterad hobbyhierarki")
    if variant >= 4:
        strengths.append("Premium/raritetsstruktur som kräver exakt variantmatchning")
    elif variant <= 1 and structure_strength < 45:
        cautions.append("Kortstrukturen är nära bas/standard och ger liten egen samlarpremie")

    if any("1/1" in t for t in tags):
        strengths.append("Dokumenterad 1/1-struktur")
    if any("Autograf" in t or "autograph" in t.casefold() for t in tags):
        strengths.append("Autografstruktur")
    if any("RPA" in t or "patch" in t.casefold() for t in tags):
        strengths.append("Patch/RPA-struktur")

    if sold >= 3 and valuation_conf >= 60:
        strengths.append("Flera verifierade jämförbara försäljningar stöder marknaden")
    elif sold == 0:
        cautions.append("Inga verifierade exakta SOLD – korttypen ensam bevisar inget värde")
    elif sold < 2:
        cautions.append("För få verifierade SOLD för robust värdebedömning")

    if identity_conf < 60:
        cautions.append("Kortidentiteten är för osäker för att veta exakt vad som samlas")
    if liquidity < 40:
        cautions.append("Svag likviditet – även ett sällsynt kort kan vara svårt att sälja")

    if grade["recognized"] and grade["strength"] >= 75:
        strengths.append("Stark grade från etablerat graderingsbolag")
    if grade.get("caution"):
        cautions.append(grade["caution"])

    # Hobby traps: visually impressive or scarce traits that are often mistaken
    # for value without enough player/market support.
    if variant >= 4 and player < 55:
        traps.append("Raritetsfälla: låg numrering/SSP räcker inte när spelarefterfrågan är svag")
    if (features.get("autograph") or any("Autograf" in t for t in tags)) and player < 55:
        traps.append("Autograffälla: en signatur på en svag spelare är inte automatiskt värdefull")
    if rookie_importance_matched and player < 55:
        traps.append("Rookiefälla: RC/rookieprogram på svag spelare kan ha låg faktisk efterfrågan")
    if structure_strength < 45 and player >= 85:
        traps.append("Stjärnspelare men standardkort: spelarnamnet gör inte varje bas/insert till ett premiumkort")
    if sold == 0 and structure_strength >= 70:
        traps.append("Premiumutseende utan marknadsbevis: exakt variant och SOLD måste verifieras")

    score = _clamp(score)
    # Hard caps prevent a flashy structure from looking elite without market proof.
    if sold == 0:
        score = min(score, 72)
    if identity_conf < 50:
        score = min(score, 58)
    if player < 45 and market_proof < 40:
        score = min(score, 52)

    if score >= 82 and market_proof >= 55:
        verdict = "STARK_SAMLARPROFIL"
        label = "Starkt samlarkort – värt seriös research"
    elif score >= 68:
        verdict = "INTRESSANT"
        label = "Samlarintressant – rätt kort kan vara värt mycket"
    elif structure_strength >= 70 and market_proof < 45:
        verdict = "RARITET_OBEKRÄFTAD"
        label = "Sällsynt/premium struktur, men marknaden är inte bekräftad"
    elif player >= 80 and structure_strength < 45:
        verdict = "SPELARDRIVET_STANDARDKORT"
        label = "Stark spelare men ganska vanligt kort"
    elif score >= 48:
        verdict = "SELEKTIVT"
        label = "Selektivt samlarintresse – köp bara med tydlig prisfördel"
    else:
        verdict = "SVAG_SAMLARPROFIL"
        label = "Svag samlarprofil – låg prioritet utan starkt prisbevis"

    value_basis = []
    if player >= 70:
        value_basis.append("spelare")
    if rookie_importance_matched and rookie >= 60:
        value_basis.append("rookieprogram")
    if variant >= 3:
        value_basis.append("raritet/parallel")
    if tags:
        value_basis.extend(tags[:2])
    if grade["strength"] >= 60:
        value_basis.append("grade")
    if sold >= 2:
        value_basis.append("verifierad marknad")

    return {
        "score": int(round(score)),
        "verdict": verdict,
        "label": label,
        "value_basis": list(dict.fromkeys(value_basis))[:6],
        "strengths": list(dict.fromkeys(strengths))[:6],
        "cautions": list(dict.fromkeys(cautions))[:6],
        "hobby_traps": list(dict.fromkeys(traps))[:5],
        "player_strength": int(round(player)),
        "structure_strength": int(round(structure_strength)),
        "market_proof_strength": int(round(market_proof)),
        "identity_strength": int(round(identity_conf)),
        "liquidity_strength": int(round(liquidity)),
        "grading_context": grade,
        "hierarchy_strength": int(round(hierarchy)),
        "hierarchy_tier": hierarchy_tier,
        "safe_for_valuation": False,
        "creates_market_value": False,
        "creates_buy_decision": False,
        "note": (
            "Collector Worth Intelligence bedömer samlarprofil och värdedrivare – inte kronor. "
            "Exakt marknadsvärde måste fortfarande komma från relevanta verifierade SOLD-comps."
        ),
    }
