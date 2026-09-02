from __future__ import annotations

from typing import Any


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def build_collector_intelligence_matrix(
    *,
    player_name: str | None,
    player_market_score: int | float | None,
    demand_tier: str | None,
    card_intelligence: dict[str, Any] | None,
    features: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine player demand and card-structure knowledge without inventing value.

    This is a triage/knowledge layer only. It may explain why a card deserves
    attention, but must never create a market price, resale estimate, profit,
    max bid, or buy decision.
    """
    features = dict(features or {})
    card_intelligence = dict(card_intelligence or {})
    player_score = _clamp(float(player_market_score or 0))
    card_tier = int(card_intelligence.get("tier", 0) or 0)
    card_score = {0: 10, 1: 25, 2: 40, 3: 58, 4: 78, 5: 95}.get(card_tier, 10)

    known_player = bool(player_name) and player_score > 0
    rookie = bool(features.get("rookie"))
    autograph = bool(features.get("autograph"))
    patch = bool(features.get("patch") or features.get("relic"))
    serial_den = features.get("serial_denominator")
    low_numbered = False
    try:
        low_numbered = serial_den is not None and int(serial_den) <= 25
    except (TypeError, ValueError):
        low_numbered = False

    # Player demand and documented card structure are deliberately balanced.
    # A premium structure for a weak/unknown player must not look like an elite card.
    if known_player:
        score = player_score * 0.55 + card_score * 0.45
    else:
        score = card_score * 0.45

    bonuses: list[str] = []
    cautions: list[str] = []

    if rookie and known_player and player_score >= 80:
        score += 4
        bonuses.append("Efterfrågad spelare + rookie-signal")
    if autograph and card_tier >= 3 and known_player and player_score >= 75:
        score += 3
        bonuses.append("Autograf i dokumenterad samlarstruktur")
    if patch and card_tier >= 4 and known_player and player_score >= 75:
        score += 2
        bonuses.append("Patch/relic i dokumenterad premiumstruktur")
    if low_numbered and known_player and player_score >= 75:
        score += 3
        bonuses.append("Låg numrering kombinerad med tydlig spelarefterfrågan")

    if not known_player:
        score = min(score, 48)
        cautions.append("Spelarefterfrågan är inte säkert identifierad")
    elif player_score < 55 and card_tier >= 4:
        score = min(score, 62)
        cautions.append("Premium kortstruktur men svag spelarefterfrågan")
    elif player_score < 70 and card_tier >= 5:
        score = min(score, 70)
        cautions.append("Mycket sällsynt struktur räcker inte ensam för stark flip-efterfrågan")

    if card_tier == 0:
        cautions.append("Ingen särskild kortstruktur i kunskapsbanken är verifierad")
    if card_tier >= 4 and not features.get("card_number"):
        cautions.append("Premiumstruktur utan verifierat kortnummer kräver extra identitetskontroll")

    score = _clamp(score)

    if score >= 88:
        level = "A-kombination"
        label = "Mycket hög samlarrelevans"
    elif score >= 76:
        level = "B-kombination"
        label = "Hög samlarrelevans"
    elif score >= 62:
        level = "C-kombination"
        label = "Förhöjd samlarrelevans"
    elif score >= 45:
        level = "D-kombination"
        label = "Selektiv samlarrelevans"
    else:
        level = "E-kombination"
        label = "Låg eller osäker samlarrelevans"

    if known_player and player_score >= 90 and card_tier >= 4:
        archetype = "Stjärna/profil + premiumstruktur"
    elif known_player and player_score >= 85 and rookie:
        archetype = "Efterfrågad spelare + rookie"
    elif card_tier >= 4 and player_score < 70:
        archetype = "Strukturdrivet kort – spelarrisken dominerar"
    elif known_player and player_score >= 85 and card_tier <= 2:
        archetype = "Spelardrivet kort – strukturen är mindre särskiljande"
    elif card_tier >= 3:
        archetype = "Känd samlarstruktur"
    else:
        archetype = "Grundkort / otillräckligt strukturunderlag"

    reasons: list[str] = []
    if known_player:
        reasons.append(f"Spelarefterfrågan: {player_score}/100 ({demand_tier or 'okänd nivå'}).")
    else:
        reasons.append("Spelarefterfrågan är inte säkert identifierad; matrisen hålls därför konservativ.")
    if card_tier:
        reasons.append(f"Kortstrukturens kunskapsnivå: {card_tier}/5 – {card_intelligence.get('level', 'känd struktur')}.")
    else:
        reasons.append("Ingen dokumenterad premiumstruktur matchade säkert i kunskapsbanken.")
    reasons.extend(bonuses[:3])
    reasons.extend(cautions[:3])

    if score >= 76:
        next_action = "Prioritera exakt identitet och exact sold comps innan köpbeslut."
    elif score >= 62:
        next_action = "Analysera vidare om priset ser fel ut, men kräv bra comps."
    else:
        next_action = "Låt inte kortets utseende eller sällsynthet ensam driva köpbeslutet."

    return {
        "score": score,
        "level": level,
        "label": label,
        "archetype": archetype,
        "reasons": reasons,
        "cautions": cautions,
        "next_action": next_action,
        "player_component": player_score,
        "card_structure_component": card_score,
        "knowledge_tier": card_tier,
        "safe_for_valuation": False,
        "note": (
            "Collector Intelligence Matrix prioriterar kombinationer av spelarefterfrågan och dokumenterad kortstruktur. "
            "Den är inte en prisguide och påverkar inte marknadsvärde, vinst eller maxbud."
        ),
    }
