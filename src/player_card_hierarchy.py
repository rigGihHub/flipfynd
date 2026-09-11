"""Player × Card Hierarchy.

Combines player-market strength with documented card hierarchy. This is a
collector-context engine, not a valuation model. It must not create market value,
ROI, max price or a BUY decision.

Important: current player-market data contains score/tier, not reliable career
status metadata. This module therefore does NOT invent "prospect/veteran/legend"
labels from names.
"""
from __future__ import annotations


def _clamp(v, lo=0, hi=100):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return float(lo)


def _player_band(score, tier):
    s=_clamp(score)
    t=str(tier or "").casefold()
    if t=="elite" or s>=90:
        return "ELITE", "Elitnivå i nuvarande spelarmarknadsdata"
    if t=="strong" or s>=75:
        return "STRONG", "Stark spelarefterfrågan"
    if t=="medium" or s>=50:
        return "MEDIUM", "Mellansegment i spelarefterfrågan"
    if s>0:
        return "WEAK", "Svag spelarefterfrågan"
    return "UNKNOWN", "Spelarefterfrågan ej säker"


def build_player_card_hierarchy(
    *,
    player_name,
    player_market_score,
    player_market_tier,
    card_hierarchy_score,
    card_hierarchy_tier,
    card_hierarchy_role,
    is_rookie=False,
    sold_comparable_count=0,
    valuation_confidence_score=0,
    identity_confidence_score=0,
):
    player_score=_clamp(player_market_score)
    card_score=_clamp(card_hierarchy_score)
    identity=_clamp(identity_confidence_score)
    valuation_conf=_clamp(valuation_confidence_score)
    sold=max(0,int(sold_comparable_count or 0))

    player_band, player_label=_player_band(player_score,player_market_tier)

    # This score measures combined collector relevance, not monetary worth.
    combined=player_score*0.52 + card_score*0.48
    if not player_name:
        combined=min(combined,55)
    if identity<50:
        combined=min(combined,62)

    reasons=[]
    cautions=[]
    traps=[]

    reasons.append(f"Spelarkomponent: {player_score:.0f}/100 – {player_label}.")
    reasons.append(f"Korthierarki: {card_score:.0f}/100 – {card_hierarchy_tier or 'okänd nivå'}.")

    role=str(card_hierarchy_role or "")
    central_role=role in {
        "FLAGSHIP_ROOKIE","PREMIUM_ROOKIE_AUTO","PREMIUM_RPA",
        "ROOKIE_PATCH_AUTO","ROOKIE_AUTOGRAPH","ROOKIE_PARALLEL",
        "ICONIC_PARALLEL_FAMILY","CHASE_SSP","ONE_OF_ONE",
    }

    if player_band=="ELITE" and central_role:
        reasons.append("Stark kombination: hög spelarefterfrågan + central/premium kortstruktur.")
    elif player_band in {"WEAK","UNKNOWN"} and card_score>=78:
        cautions.append("Stark kortstruktur men svag/okänd spelarefterfrågan – strukturen ensam räcker inte.")
        traps.append("Programfälla: ett prestigefyllt set gör inte varje spelare till ett starkt samlarobjekt.")
    elif player_band=="ELITE" and card_score<45:
        cautions.append("Stark spelare men ordinär kortstruktur.")
        traps.append("Stjärnfälla: en elitspelare gör inte varje bas/standardkort premium.")

    if is_rookie and central_role and player_band in {"ELITE","STRONG"}:
        reasons.append("Rookie-status sammanfaller med ett relevant program och stark spelarefterfrågan.")
    elif is_rookie and player_band in {"WEAK","UNKNOWN"}:
        cautions.append("Rookie-status utan stark spelarefterfrågan är inte automatiskt värdefull.")

    market_proof = min(100.0, sold*20.0) * 0.65 + valuation_conf*0.35
    if sold>=3 and valuation_conf>=60:
        reasons.append("Flera verifierade SOLD ger marknadsstöd åt kombinationen.")
    elif sold==0:
        cautions.append("Inga verifierade exakta SOLD – kombinationen är samlarkontext, inte prisbevis.")

    # Market proof affects confidence in the profile, not collector relevance itself.
    confidence=identity*0.45 + min(100,sold*18)*0.35 + valuation_conf*0.20

    if combined>=86 and player_band=="ELITE" and card_score>=78:
        profile="ELITE_X_PREMIUM"
        label="Elitspelare × stark korthierarki"
    elif combined>=76 and player_band in {"ELITE","STRONG"} and card_score>=65:
        profile="STRONG_X_RELEVANT"
        label="Stark spelare × relevant samlarprogram"
    elif player_band=="ELITE" and card_score<45:
        profile="STAR_X_STANDARD"
        label="Stjärnspelare × standardkort"
    elif card_score>=78 and player_band in {"WEAK","UNKNOWN"}:
        profile="PREMIUM_X_WEAK_PLAYER"
        label="Premiumstruktur × svag/okänd spelare"
    elif combined>=58:
        profile="SELECTIVE"
        label="Selektiv spelare × kort-kombination"
    else:
        profile="LOW_PRIORITY"
        label="Svag kombinerad samlarprofil"

    return {
        "score":int(round(_clamp(combined))),
        "confidence_score":int(round(_clamp(confidence))),
        "profile":profile,
        "label":label,
        "player_band":player_band,
        "player_band_label":player_label,
        "card_role":role or None,
        "market_proof_score":int(round(_clamp(market_proof))),
        "reasons":list(dict.fromkeys(reasons))[:6],
        "cautions":list(dict.fromkeys(cautions))[:6],
        "hobby_traps":list(dict.fromkeys(traps))[:5],
        "career_status":None,
        "career_status_note":"Karriärstatus anges inte eftersom nuvarande spelardata saknar verifierad career-status metadata.",
        "safe_for_valuation":False,
        "creates_market_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
        "note":"Player × Card Hierarchy beskriver samlarrelevans för kombinationen spelare + korttyp. Verifierade SOLD krävs för pris.",
    }
