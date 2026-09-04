"""Decision Conflict Audit for FlipFynd.

The audit looks for contradictions between an apparently attractive deal and
weak downside, liquidity, risk or evidence signals. It never creates a buy,
valuation or ranking boost. Its only directional effect is to downgrade a
clear KÖP to KANSKE when contradictions are severe enough.
"""
from __future__ import annotations

from typing import Any

BUY_DECISIONS = {"KÖP", "KÖP (starkt fynd)"}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def audit_decision_conflicts(
    *,
    decision: str,
    deal_score: float,
    risk_score: float,
    liquidity_score: float,
    valuation_confidence_score: float,
    identity_confidence_score: float,
    sale_probability: float,
    net_profit_estimate: float,
    floor_profit_estimate: float,
    risk_adjusted_profit: float,
    roi_estimate: float,
    comp_valuation_basis: str = "none",
    sold_comparable_count: int = 0,
) -> dict[str, Any]:
    """Return transparent contradictions between opportunity and evidence.

    This is intentionally conservative and mostly descriptive. A clear buy is
    only downgraded for a hard contradiction, or when several independent
    moderate contradictions are present at the same time.
    """
    raw_decision = str(decision or "SKIP")
    deal = max(0.0, min(100.0, _num(deal_score)))
    risk = max(0.0, min(100.0, _num(risk_score)))
    liquidity = max(0.0, min(100.0, _num(liquidity_score)))
    valuation = max(0.0, min(100.0, _num(valuation_confidence_score)))
    identity = max(0.0, min(100.0, _num(identity_confidence_score)))
    probability = max(0.0, min(100.0, _num(sale_probability)))
    net_profit = _num(net_profit_estimate)
    floor_profit = _num(floor_profit_estimate)
    risk_adjusted = _num(risk_adjusted_profit)
    roi = _num(roi_estimate)
    basis = str(comp_valuation_basis or "none").casefold()
    sold_count = max(0, int(sold_comparable_count or 0))

    conflicts: list[dict[str, str]] = []
    strengths: list[str] = []

    def add(code: str, severity: str, message: str) -> None:
        conflicts.append({"code": code, "severity": severity, "message": message})

    # Opportunity score vs execution risk.
    if deal >= 80 and risk >= 60:
        add(
            "high_score_high_risk",
            "moderate" if risk < 70 else "hard",
            f"hög fyndpoäng ({deal:.0f}/100) motsägs av hög risk ({risk:.0f}/100)",
        )
    elif deal >= 70 and risk >= 65:
        add(
            "good_score_high_risk",
            "moderate",
            f"bra fyndpoäng ({deal:.0f}/100) kombineras med förhöjd risk ({risk:.0f}/100)",
        )

    # Apparent upside vs ability to resell.
    if deal >= 75 and liquidity < 35:
        add(
            "high_score_low_liquidity",
            "hard" if liquidity < 25 else "moderate",
            f"hög fyndpoäng ({deal:.0f}/100) motsägs av låg säljbarhet ({liquidity:.0f}/100)",
        )
    elif net_profit >= 75 and liquidity < 40:
        add(
            "profit_low_liquidity",
            "moderate",
            f"beräknad vinst är positiv men säljbarheten är låg ({liquidity:.0f}/100)",
        )

    # Expected case vs downside case.
    if net_profit > 0 and risk_adjusted <= 0:
        add(
            "positive_expected_negative_risk_adjusted",
            "hard",
            "förväntad vinst är positiv men riskjusterad vinst är inte positiv",
        )
    if net_profit >= 75 and floor_profit <= 0:
        severity = "hard" if floor_profit <= -50 and risk >= 55 else "moderate"
        add(
            "positive_expected_negative_floor",
            severity,
            f"förväntad vinst är positiv men golvscenariot är {floor_profit:.0f} kr",
        )

    # Buy signal vs probability of actually completing a resale.
    if raw_decision in BUY_DECISIONS and probability < 45:
        add(
            "buy_low_sale_probability",
            "hard",
            f"KÖP-signalen motsägs av låg beräknad säljchans ({probability:.0f} %)",
        )
    elif deal >= 75 and probability < 55:
        add(
            "high_score_moderate_sale_probability",
            "moderate",
            f"hög fyndpoäng kombineras med bara {probability:.0f} % beräknad säljchans",
        )

    # Strong-looking deal vs middling evidence. Confidence Audit catches truly
    # weak evidence; this catches the contradiction when the opportunity score
    # still looks unusually strong relative to the evidence quality.
    if deal >= 80 and valuation < 55:
        add(
            "high_score_thin_valuation",
            "moderate",
            f"mycket hög fyndpoäng stöds bara av {valuation:.0f}/100 i värderingssäkerhet",
        )
    if deal >= 80 and identity < 65:
        add(
            "high_score_thin_identity",
            "moderate",
            f"mycket hög fyndpoäng kombineras med bara {identity:.0f}/100 i identitetssäkerhet",
        )

    if deal >= 75 and basis in {"none", "asking", "current", "current_listings", "listings"} and sold_count == 0:
        add(
            "high_score_without_sold_support",
            "moderate",
            "hög fyndpoäng saknar stöd från verifierade sålda jämförelseobjekt",
        )

    # A very high ROI can be real, but in combination with thin evidence it is
    # a classic contradiction worth surfacing instead of celebrating blindly.
    if roi >= 1.0 and valuation < 60:
        add(
            "extreme_roi_thin_evidence",
            "moderate",
            f"mycket hög beräknad ROI ({roi * 100:.0f} %) vilar på begränsad värderingssäkerhet",
        )

    if risk < 45:
        strengths.append(f"risknivån är hanterbar ({risk:.0f}/100)")
    if liquidity >= 60:
        strengths.append(f"säljbarheten stödjer caset ({liquidity:.0f}/100)")
    if floor_profit > 0:
        strengths.append(f"även golvscenariot är positivt ({floor_profit:.0f} kr)")
    if valuation >= 65 and identity >= 70:
        strengths.append("värdering och identitet har relativt starkt stöd")
    if sold_count >= 2 and basis == "sold":
        strengths.append(f"{sold_count} verifierade sålda comps stödjer prisbilden")

    hard_count = sum(1 for x in conflicts if x["severity"] == "hard")
    moderate_count = sum(1 for x in conflicts if x["severity"] == "moderate")
    severe = hard_count >= 1 or moderate_count >= 3

    audited_decision = raw_decision
    downgraded = False
    if raw_decision in BUY_DECISIONS and severe:
        audited_decision = "KANSKE"
        downgraded = True

    if severe:
        status = "MOTSÄGELSE"
        label = "Ser attraktivt ut, men signalerna motsäger ett klart KÖP"
        summary = "Ser billigt ut, men risk, nedsida eller evidens räcker inte för ett klart KÖP."
    elif conflicts:
        status = "BLANDAD"
        label = "Potential finns, men signalerna drar åt olika håll"
        summary = "Potential finns, men signalerna drar åt olika håll – verifiera innan köp."
    else:
        status = "KONSEKVENT"
        label = "Analysen är inbördes konsekvent"
        summary = "Pris, risk, säljbarhet och evidens pekar i huvudsak åt samma håll."

    return {
        "status": status,
        "label": label,
        "summary": summary,
        "original_decision": raw_decision,
        "audited_decision": audited_decision,
        "downgraded": downgraded,
        "severe_conflict": severe,
        "hard_conflict_count": hard_count,
        "moderate_conflict_count": moderate_count,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "strengths": strengths,
        "allow_max_purchase": not severe,
        "automatic_weight_changes": False,
        "note": (
            "Decision Conflict Audit skapar inga värden och kan aldrig uppgradera ett beslut. "
            "Den letar bara efter motsägelser mellan fyndsignal, risk, säljbarhet, nedsida och evidens."
        ),
    }
