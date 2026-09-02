from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "player_card_demand.json"


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def _load_config() -> dict[str, Any]:
    try:
        with DATA_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _structure_score(variant_rung: int, rookie_rung: int, chase_priority: int) -> tuple[int, str]:
    cfg = _load_config()
    archetypes = cfg.get("archetypes", {}) if isinstance(cfg, dict) else {}
    mapping = {
        0: ("base_or_unknown", 20),
        1: ("known_program", 35),
        2: ("parallel", 50),
        3: ("numbered_or_auto", 65),
        4: ("ssp_or_premium", 78),
        5: ("low_numbered_or_grail", 90),
        6: ("one_of_one", 96),
    }
    key, fallback = mapping.get(int(variant_rung or 0), mapping[0])
    row = archetypes.get(key, {}) if isinstance(archetypes, dict) else {}
    score = int(row.get("structure_score", fallback) or fallback)
    label = str(row.get("label") or key)

    rookie_bonus_map = cfg.get("rookie_bonuses", {}) if isinstance(cfg, dict) else {}
    rookie_bonus = 0
    if isinstance(rookie_bonus_map, dict):
        rookie_bonus = int(rookie_bonus_map.get(str(int(rookie_rung or 0)), 0) or 0)
    score += rookie_bonus

    # Chase knowledge is only corroborating structural attention; it is not a price signal.
    if int(chase_priority or 0) >= 80:
        score += 5
    elif int(chase_priority or 0) >= 60:
        score += 3

    return _clamp(score), label


def build_player_card_demand(
    *,
    player_name: str | None,
    player_market_score: int | float | None,
    demand_tier: str | None,
    variant_rung: int | None,
    rookie_rung: int | None,
    chase_priority_score: int | None,
    sold_comparable_count: int | None,
    asking_comparable_count: int | None,
    liquidity_score: int | float | None,
    sold_30d: int | None = None,
    sold_90d: int | None = None,
    identity_confidence_score: int | float | None = None,
    valuation_confidence_score: int | float | None = None,
) -> dict[str, Any]:
    """Estimate demand *attention*, never price.

    The score combines a player-demand prior, structural collector demand and
    observed turnover evidence. Missing sold data is treated as uncertainty,
    not proof that a card has no demand.
    """
    player_score = _clamp(float(player_market_score or 0))
    identity_conf = _clamp(float(identity_confidence_score or 0))
    valuation_conf = _clamp(float(valuation_confidence_score or 0))
    liquidity = _clamp(float(liquidity_score or 0))
    sold_count = max(0, int(sold_comparable_count or 0))
    asking_count = max(0, int(asking_comparable_count or 0))
    recent_30 = max(0, int(sold_30d or 0))
    recent_90 = max(0, int(sold_90d or 0))

    structure_score, structure_label = _structure_score(
        int(variant_rung or 0), int(rookie_rung or 0), int(chase_priority_score or 0)
    )

    # Market evidence should reward observed turnover but never make missing
    # sold data look like zero demand. Neutral prior = 50 when no sold evidence.
    if sold_count >= 6 or recent_30 >= 3:
        market_score = max(78, liquidity)
        market_evidence = "Starkt observerat omsättningsstöd"
    elif sold_count >= 3 or recent_90 >= 3:
        market_score = max(68, liquidity)
        market_evidence = "Tydligt observerat omsättningsstöd"
    elif sold_count >= 1:
        market_score = max(58, min(75, liquidity))
        market_evidence = "Visst observerat omsättningsstöd"
    elif asking_count >= 3:
        market_score = 52
        market_evidence = "Endast utbudsdata – faktisk omsättning ej verifierad"
    else:
        market_score = 50
        market_evidence = "Otillräckligt omsättningsunderlag"

    known_player = bool(player_name) and player_score > 0
    demand_score = player_score * 0.50 + structure_score * 0.30 + market_score * 0.20

    reasons: list[str] = []
    cautions: list[str] = []
    if known_player:
        reasons.append(f"Spelarefterfrågan: {player_score}/100 ({demand_tier or 'okänd nivå'}).")
    else:
        demand_score = min(demand_score, 55)
        cautions.append("Spelaren är inte säkert identifierad; efterfrågan hålls konservativ.")

    reasons.append(f"Kortstruktur: {structure_score}/100 – {structure_label}.")
    reasons.append(f"Marknadsevidens: {market_score}/100 – {market_evidence}.")

    if sold_count:
        reasons.append(f"{sold_count} matchande sålda comp(s) finns i underlaget.")
    elif asking_count:
        cautions.append("Aktiva annonser visar utbud, inte att kortet faktiskt säljer.")
    else:
        cautions.append("Inga verifierade sold comps; efterfrågan är en prioriteringssignal, inte ett bevis.")

    if int(variant_rung or 0) >= 4 and player_score < 60:
        demand_score = min(demand_score, 68)
        cautions.append("Sällsynt struktur kombineras med svag/okänd spelarefterfrågan.")
    if identity_conf < 50:
        demand_score = min(demand_score, 64)
        cautions.append("Kortidentiteten är för osäker för stark efterfrågeklassning.")

    demand_score = _clamp(demand_score)

    # Confidence answers a separate question: how much evidence supports the
    # demand classification? It is intentionally low without sold turnover.
    sold_evidence_conf = min(100, sold_count * 14 + recent_90 * 5)
    if sold_count == 0:
        sold_evidence_conf = 20 if asking_count else 10
    demand_confidence = _clamp(
        identity_conf * 0.35 + valuation_conf * 0.25 + sold_evidence_conf * 0.30 + (80 if known_player else 25) * 0.10
    )

    if demand_score >= 85 and demand_confidence >= 65:
        profile = "Stark och verifierad efterfrågan"
    elif demand_score >= 80 and player_score >= structure_score:
        profile = "Spelardriven efterfrågan"
    elif demand_score >= 75 and structure_score > player_score:
        profile = "Korttypsdriven efterfrågan"
    elif demand_score >= 65:
        profile = "Lovande efterfrågan – verifiera omsättning"
    elif demand_score >= 50:
        profile = "Selektiv/normal efterfrågan"
    else:
        profile = "Svag eller osäker efterfrågan"

    # Triage priority can be used to choose which listings deserve full analysis.
    # It deliberately discounts weak evidence and may never change final value/rank.
    confidence_factor = 0.55 + (demand_confidence / 100.0) * 0.45
    review_priority = _clamp(demand_score * confidence_factor)
    preselection_boost = min(12, max(0, round((review_priority - 55) / 4)))

    if review_priority >= 78:
        action = "Prioritera full analys och exact sold comps."
    elif review_priority >= 65:
        action = "Ta med i fördjupad analys om priset ser avvikande ut."
    else:
        action = "Låt pris/comps avgöra; efterfrågesignalen ensam räcker inte."

    return {
        "score": demand_score,
        "confidence_score": demand_confidence,
        "profile": profile,
        "review_priority_score": review_priority,
        "preselection_boost": preselection_boost,
        "player_component": player_score,
        "structure_component": structure_score,
        "market_component": market_score,
        "market_evidence": market_evidence,
        "reasons": reasons[:6],
        "cautions": cautions[:6],
        "next_action": action,
        "safe_for_valuation": False,
        "note": (
            "Player × Card Demand Engine mäter sannolik samlar-/köparefterfrågan och analysprioritet. "
            "Den är inte en prisguide och får inte höja marknadsvärde, vinst, ROI eller maxbud."
        ),
    }
