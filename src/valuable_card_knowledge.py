from __future__ import annotations

from typing import Any


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def _tag_signal(signal: dict[str, Any]) -> list[str]:
    category = str(signal.get("category") or "").casefold()
    rarity = str(signal.get("rarity_signal") or "").casefold()
    label = str(signal.get("label") or "").casefold()
    text = f"{category} {rarity} {label}"
    tags: list[str] = []
    if "rookie_patch_auto" in category or ("rookie" in text and "patch" in text and "auto" in text):
        tags.append("RPA / rookie patch auto")
    elif "rookie_auto" in category or ("rookie" in text and "auto" in text):
        tags.append("Rookie autograph")
    elif "rookie" in text:
        tags.append("Rookie-program")
    if "case_hit" in category or "ssp" in category or "grail" in category or "case_level" in rarity or "ultra_rare" in rarity:
        tags.append("SSP / case hit")
    if "autograph" in category or "auto" in text:
        tags.append("Autograf")
    if "relic" in category or "memorabilia" in category or "patch" in text:
        tags.append("Relic / patch")
    run = signal.get("print_run")
    if isinstance(run, int) and run > 0:
        if run == 1:
            tags.append("1/1")
        elif run <= 10:
            tags.append("Mycket låg numrering")
        elif run <= 25:
            tags.append("Låg numrering")
        elif run <= 100:
            tags.append("Numrerad parallel")
    return list(dict.fromkeys(tags))


def build_valuable_card_knowledge(
    *,
    signals: list[dict] | None,
    player_name: str | None,
    player_market_score: int | float | None,
    variant_rung: int | None,
    rookie_rung: int | None,
    sold_comparable_count: int | None,
    valuation_confidence_score: int | float | None,
    identity_confidence_score: int | float | None,
    risk_score: int | float | None,
) -> dict[str, Any]:
    """Classify whether a card deserves extra *value research* attention.

    This is deliberately not a price model. It identifies archetypes that often
    warrant exact-card sold-comps research, while market value still comes only
    from actual comparable evidence.
    """
    rows = [dict(s) for s in (signals or []) if isinstance(s, dict)]
    player_score = _clamp(float(player_market_score or 0))
    variant = max(0, int(variant_rung or 0))
    rookie = max(0, int(rookie_rung or 0))
    sold = max(0, int(sold_comparable_count or 0))
    valuation_conf = _clamp(float(valuation_confidence_score or 0))
    identity_conf = _clamp(float(identity_confidence_score or 0))
    risk = _clamp(float(risk_score or 0))

    tags: list[str] = []
    for row in rows:
        tags.extend(_tag_signal(row))
    tags = list(dict.fromkeys(tags))

    structure = 18
    if variant >= 6:
        structure = 98
    elif variant >= 5:
        structure = 90
    elif variant >= 4:
        structure = 78
    elif variant >= 3:
        structure = 64
    elif variant >= 2:
        structure = 48
    elif rows:
        structure = 34
    if rookie >= 5:
        structure = min(100, structure + 12)
    elif rookie >= 4:
        structure = min(100, structure + 9)
    elif rookie >= 2:
        structure = min(100, structure + 5)

    # This score is an investigation priority, not estimated monetary worth.
    priority = player_score * 0.42 + structure * 0.38 + identity_conf * 0.12 + min(100, sold * 18) * 0.08
    if not player_name:
        priority = min(priority, 58)
    if identity_conf < 45:
        priority = min(priority, 62)
    if risk >= 75:
        priority = min(priority, 70)
    priority = _clamp(priority)

    if "RPA / rookie patch auto" in tags:
        archetype = "Rookie Patch Auto – exact identitet och sold comps krävs"
    elif "Rookie autograph" in tags:
        archetype = "Rookie Autograph – potentiellt stark korttyp"
    elif "1/1" in tags:
        archetype = "1/1 – unik variant, mycket svår att värdera utan närliggande evidens"
    elif "SSP / case hit" in tags:
        archetype = "SSP / case hit – chase-kort att prioritera för exakt identifiering"
    elif "Mycket låg numrering" in tags or "Låg numrering" in tags:
        archetype = "Lågnumrerad variant – spelar- och variantmatchning är avgörande"
    elif "Rookie-program" in tags:
        archetype = "Rookieprogram – kontrollera om detta är spelarens centrala rookie-kort"
    elif "Autograf" in tags:
        archetype = "Autografkort – efterfrågan beror starkt på spelare och program"
    elif rows:
        archetype = "Känd samlarstruktur – verifiera om marknaden betalar premium"
    else:
        archetype = "Ingen särskild värdekortstyp identifierad"

    if sold >= 4 and valuation_conf >= 65:
        evidence = "Starkt marknadsstöd"
        evidence_score = max(75, valuation_conf)
    elif sold >= 2 and valuation_conf >= 45:
        evidence = "Visst marknadsstöd"
        evidence_score = max(55, valuation_conf)
    elif sold >= 1:
        evidence = "Begränsat marknadsstöd"
        evidence_score = min(60, max(35, valuation_conf))
    else:
        evidence = "Otillräckligt underlag"
        evidence_score = min(35, valuation_conf)

    reasons: list[str] = []
    if player_name:
        reasons.append(f"Spelarefterfrågan är {player_score}/100 för {player_name}.")
    else:
        reasons.append("Spelaren är inte säkert identifierad; värdekortsklassningen hålls tillbaka.")
    if tags:
        reasons.append("Korttyp: " + ", ".join(tags[:4]) + ".")
    if rows:
        labels = [str(r.get("label")) for r in rows if r.get("label")]
        if labels:
            reasons.append("Kunskapsmatchning: " + ", ".join(labels[:3]) + ".")
    reasons.append(f"Marknadsevidens: {evidence} ({sold} verifierade sold comps i aktuellt underlag).")

    cautions: list[str] = []
    if sold == 0:
        cautions.append("Ingen värdenivå får antas från korttypen ensam; exakta sold comps saknas.")
    if identity_conf < 60:
        cautions.append("Kortidentiteten är inte tillräckligt stark för aggressiv comp-användning.")
    if risk >= 65:
        cautions.append("Riskmodellen är förhöjd; prioritera verifiering före köpbeslut.")
    if variant >= 4:
        cautions.append("Bas- och syskonvarianter får inte användas som exakta comps för denna struktur.")

    if priority >= 80:
        level = "Mycket hög granskningsprioritet"
    elif priority >= 68:
        level = "Hög granskningsprioritet"
    elif priority >= 55:
        level = "Förhöjd granskningsprioritet"
    else:
        level = "Normal granskningsprioritet"

    return {
        "priority_score": priority,
        "level": level,
        "archetype": archetype,
        "tags": tags[:8],
        "structure_score": structure,
        "player_score": player_score,
        "market_evidence": evidence,
        "market_evidence_score": _clamp(evidence_score),
        "reasons": reasons[:6],
        "cautions": cautions[:6],
        "safe_for_valuation": False,
        "note": (
            "Valuable Card Knowledge Engine identifierar korttyper som bör värdeundersökas extra. "
            "Den skapar aldrig marknadsvärde, vinst, ROI eller maxbud utan marknadsevidens."
        ),
    }
