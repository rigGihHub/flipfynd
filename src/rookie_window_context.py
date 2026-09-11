"""Rookie Window & Player Archetype.

Uses verified Player Knowledge plus card season/year to describe *career-window
context*. It does not invent a debut season or official rookie year.

Important:
- explicit RC/rookie detection remains separate;
- age-at-card-season can support or contradict a rookie claim, but cannot prove
  official rookie status;
- no output creates monetary value, ROI, max price or BUY.
"""
from __future__ import annotations
import re
from datetime import date


def _year(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value if 1900 <= value <= 2100 else None
    text=str(value).strip()
    m=re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if not m:
        return None
    return int(m.group(1))


def _birth_year(player_knowledge):
    dob=str((player_knowledge or {}).get("date_of_birth") or "")
    m=re.match(r"^(19\d{2}|20\d{2})-", dob)
    return int(m.group(1)) if m else None


def _season_year(features):
    features=features or {}
    # Prefer season/year already parsed by FlipFynd.
    for key in ("season","year"):
        y=_year(features.get(key))
        if y:
            return y
    return None


def build_rookie_window_context(*, features, player_knowledge, player_market_score=0, player_market_tier=None):
    features=dict(features or {})
    knowledge=dict(player_knowledge or {})

    card_year=_season_year(features)
    born=_birth_year(knowledge)
    explicit_rookie=bool(features.get("is_rookie"))
    verified_player=bool(knowledge.get("verified"))
    lifecycle=str(knowledge.get("career_status") or "")
    activity=str(knowledge.get("activity_status") or "")

    age_at_card=None
    if card_year and born:
        age_at_card=card_year-born

    reasons=[]
    cautions=[]

    if card_year:
        reasons.append(f"Kortets observerade säsongs-/årsfönster börjar {card_year}.")
    if age_at_card is not None:
        reasons.append(f"Spelaren var ungefär {age_at_card} år vid kortets säsongsstart.")

    # Career window is descriptive, not an official hobby rookie designation.
    if age_at_card is None:
        window="UNKNOWN"
        label="Karriärfönster okänt"
    elif age_at_card < 15:
        window="CHRONOLOGY_CONFLICT"
        label="Kronologikonflikt"
        cautions.append("Kortåret ligger orimligt tidigt relativt verifierat födelseår; identiteten eller året bör kontrolleras.")
    elif age_at_card <= 23:
        window="YOUNG_WINDOW"
        label="Ungt karriärfönster"
    elif age_at_card <= 30:
        window="PRIME_AGE_WINDOW"
        label="Prime-age-fönster"
    elif age_at_card <= 35:
        window="ESTABLISHED_WINDOW"
        label="Etablerat karriärfönster"
    else:
        window="LATE_OR_HISTORICAL_WINDOW"
        label="Sent/historiskt karriärfönster"

    rookie_support="UNPROVEN"
    if explicit_rookie:
        if age_at_card is not None and 16 <= age_at_card <= 23:
            rookie_support="CHRONOLOGICALLY_PLAUSIBLE"
            reasons.append("RC/rookie-anspråket är kronologiskt rimligt, men officiellt rookieår är inte verifierat här.")
        elif age_at_card is not None and age_at_card >= 27:
            rookie_support="CHRONOLOGICALLY_SUSPICIOUS"
            cautions.append("RC/rookie-anspråket ser kronologiskt tveksamt ut och bör verifieras mot officiellt checklist-/rookieprogram.")
        else:
            cautions.append("RC/rookie-anspråket saknar tillräcklig karriärdata för att styrkas.")
    else:
        if window=="YOUNG_WINDOW":
            reasons.append("Kortet ligger tidigt i karriäråldern men är inte automatiskt ett rookie-kort.")

    score=float(player_market_score or 0)
    tier=str(player_market_tier or "").casefold()

    # Archetype is based on verified lifecycle facts + existing market band.
    # Do not invent 'legend' unless career_status explicitly says so.
    if lifecycle in {"retired_legend","active_legend"}:
        archetype="LEGEND"
        archetype_label="Verifierad legendprofil"
    elif activity=="active" and age_at_card is not None and age_at_card <= 23 and (tier in {"elite","strong"} or score >= 75):
        archetype="YOUNG_HIGH_DEMAND"
        archetype_label="Ung spelare med stark efterfrågan"
    elif activity=="active" and (tier=="elite" or score >= 90):
        archetype="ACTIVE_ELITE"
        archetype_label="Aktiv elitspelare"
    elif activity=="active" and (tier=="strong" or score >= 75):
        archetype="ACTIVE_STRONG"
        archetype_label="Aktiv spelare med stark efterfrågan"
    elif activity=="active":
        archetype="ACTIVE_OTHER"
        archetype_label="Aktiv spelare"
    elif activity=="retired":
        archetype="RETIRED"
        archetype_label="Pensionerad spelare"
    else:
        archetype="UNKNOWN"
        archetype_label="Spelararketyp okänd"

    # Research relevance only. This cannot create value or BUY.
    if window=="YOUNG_WINDOW" and archetype in {"YOUNG_HIGH_DEMAND","ACTIVE_ELITE","ACTIVE_STRONG"}:
        research_priority="HIGH"
        reasons.append("Ungt karriärfönster + stark spelarefterfrågan gör exakt kortidentitet extra viktig att verifiera.")
    elif archetype=="LEGEND" and explicit_rookie:
        research_priority="HIGH"
        reasons.append("Rookie-anspråk på verifierad legendprofil kräver särskilt stark checklist-/programverifiering.")
    elif window=="CHRONOLOGY_CONFLICT" or rookie_support=="CHRONOLOGICALLY_SUSPICIOUS":
        research_priority="HIGH"
    else:
        research_priority="NORMAL"

    return {
        "card_year":card_year,
        "age_at_card_season":age_at_card,
        "career_window":window,
        "career_window_label":label,
        "explicit_rookie_claim":explicit_rookie,
        "rookie_claim_support":rookie_support,
        "player_archetype":archetype,
        "player_archetype_label":archetype_label,
        "research_priority":research_priority,
        "reasons":list(dict.fromkeys(reasons))[:7],
        "cautions":list(dict.fromkeys(cautions))[:6],
        "verified_player_knowledge":verified_player,
        "official_rookie_year":None,
        "official_rookie_year_verified":False,
        "safe_for_valuation":False,
        "creates_market_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
        "note":"Karriärfönster och spelararketyp ger samlarkontext. Officiellt rookieår måste verifieras separat via checklist-/programdata.",
    }
