"""Explain how close an analysed listing is to FlipFynd's normal KÖP threshold.

The module is intentionally read-only: it summarizes already computed fields and
never changes valuation, decision, ranking, max bid, or deal score.
"""
from __future__ import annotations

from typing import Any


BUY_THRESHOLDS = {
    "confidence": 0.28,
    "risk_adjusted_profit": 20.0,
    "sale_probability": 55.0,
    "net_profit_estimate": 30.0,
    "roi_estimate": 0.18,
    "downside_ratio": -0.25,
}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _identity_blocker(item: dict) -> str | None:
    status = str(item.get("exact_identity_gate_status") or "").upper()
    score = _num(item.get("exact_identity_gate_score"), item.get("card_identity_confidence_score", 0))
    if status in {"LÅST", "GRANSKA"} or score < 55:
        blockers = item.get("exact_identity_gate_blockers") or []
        if blockers:
            return f"Verifiera kortidentiteten: {blockers[0]}"
        return "Verifiera exakt spelare, set/program, variant och kortnummer."
    return None


def _valuation_blocker(item: dict) -> str | None:
    valuation = _num(item.get("valuation_confidence_score"), item.get("valuation_confidence", 0))
    sold = int(_num(item.get("sold_comparable_count"), 0))
    comps = int(_num(item.get("comparable_count"), 0))
    if sold < 2:
        missing = max(0, 2 - sold)
        return f"Behöver minst {missing} ytterligare verifierad försäljning som jämförelse." if sold else "Behöver minst 2 verifierade sålda jämförelsekort."
    if valuation < 60:
        return f"Prisunderlaget är för osäkert ({valuation:.0f}/100); sikta på minst 60/100."
    if comps < 2:
        return "Behöver fler relevanta jämförelser innan prisbilden är stabil."
    return None


def _economic_gaps(item: dict) -> list[dict]:
    gaps: list[dict] = []
    confidence = _num(item.get("confidence"), 0)
    risk_adjusted = _num(item.get("risk_adjusted_profit"), 0)
    probability = _num(item.get("sale_probability"), 0)
    net = _num(item.get("net_profit_estimate"), 0)
    roi = _num(item.get("roi_estimate"), 0)
    total = max(_num(item.get("analysis_total_cost"), item.get("total_cost", 0)), 1.0)
    floor = _num(item.get("floor_profit_estimate"), 0)
    downside = floor / total

    if confidence < BUY_THRESHOLDS["confidence"]:
        gaps.append({"key": "confidence", "label": "Analyssäkerhet", "current": confidence, "target": BUY_THRESHOLDS["confidence"], "unit": "%"})
    if risk_adjusted < BUY_THRESHOLDS["risk_adjusted_profit"]:
        gaps.append({"key": "risk_adjusted_profit", "label": "Riskjusterad vinst", "current": risk_adjusted, "target": BUY_THRESHOLDS["risk_adjusted_profit"], "unit": "kr"})
    if probability < BUY_THRESHOLDS["sale_probability"]:
        gaps.append({"key": "sale_probability", "label": "Säljchans", "current": probability, "target": BUY_THRESHOLDS["sale_probability"], "unit": "%"})
    if net < BUY_THRESHOLDS["net_profit_estimate"]:
        gaps.append({"key": "net_profit_estimate", "label": "Förväntad nettovinst", "current": net, "target": BUY_THRESHOLDS["net_profit_estimate"], "unit": "kr"})
    if roi < BUY_THRESHOLDS["roi_estimate"]:
        gaps.append({"key": "roi_estimate", "label": "ROI", "current": roi, "target": BUY_THRESHOLDS["roi_estimate"], "unit": "%"})
    if downside < BUY_THRESHOLDS["downside_ratio"]:
        gaps.append({"key": "downside_ratio", "label": "Nedsida", "current": downside, "target": BUY_THRESHOLDS["downside_ratio"], "unit": "%"})
    return gaps


def _format_gap(gap: dict) -> str:
    current, target, unit = gap["current"], gap["target"], gap["unit"]
    if gap["key"] in {"confidence", "roi_estimate", "downside_ratio"}:
        return f"{gap['label']}: {current:.0%} → minst {target:.0%}"
    if unit == "%":
        return f"{gap['label']}: {current:.0f}% → minst {target:.0f}%"
    return f"{gap['label']}: {current:.0f} kr → minst {target:.0f} kr"


def _readiness_score(item: dict, identity_blocked: bool, valuation_blocked: bool, gaps: list[dict]) -> int:
    if str(item.get("beslut") or "").startswith("KÖP"):
        return 100

    # Score proximity to the known KÖP thresholds. Evidence blockers cap the
    # display score so an economically attractive but unverified card cannot
    # look "almost buy-ready".
    confidence = min(1.0, _num(item.get("confidence")) / BUY_THRESHOLDS["confidence"])
    rap = min(1.0, max(0.0, _num(item.get("risk_adjusted_profit"))) / BUY_THRESHOLDS["risk_adjusted_profit"])
    probability = min(1.0, _num(item.get("sale_probability")) / BUY_THRESHOLDS["sale_probability"])
    net = min(1.0, max(0.0, _num(item.get("net_profit_estimate"))) / BUY_THRESHOLDS["net_profit_estimate"])
    roi = min(1.0, max(0.0, _num(item.get("roi_estimate"))) / BUY_THRESHOLDS["roi_estimate"])
    score = round((confidence * 15 + rap * 25 + probability * 15 + net * 20 + roi * 25))
    if identity_blocked:
        score = min(score, 49)
    if valuation_blocked:
        score = min(score, 59)
    if len(gaps) >= 4:
        score = min(score, 45)
    return int(max(0, min(99, score)))


def build_near_buy_guidance(item: dict) -> dict:
    """Return user-facing guidance for an already analysed listing."""
    decision = str(item.get("beslut") or "SKIP")
    if decision.startswith("KÖP"):
        return {
            "readiness_score": 100,
            "status": "KÖP-KLAR",
            "primary_action": "Kortet når redan FlipFynds köpgräns. Följ maxbud och verifieringskrav innan köp.",
            "blockers": [],
            "threshold_gaps": [],
            "next_steps": [],
            "safe_for_valuation": False,
        }

    identity = _identity_blocker(item)
    valuation = _valuation_blocker(item)
    gaps = _economic_gaps(item)
    blockers = [x for x in (identity, valuation) if x]

    next_steps: list[str] = []
    if identity:
        next_steps.append(identity)
    if valuation:
        next_steps.append(valuation)
    for gap in gaps[:3]:
        next_steps.append(_format_gap(gap))

    readiness = _readiness_score(item, bool(identity), bool(valuation), gaps)
    if identity:
        status = "VERIFIERA IDENTITET"
        primary = "Börja med att säkerställa exakt vilket kort det är. Prisjämförelser är sekundära tills identiteten håller."
    elif valuation:
        status = "MER PRISUNDERLAG"
        primary = "Kortidentiteten ser användbar ut, men prisunderlaget är inte starkt nog för KÖP."
    elif gaps:
        status = "NÄRA KÖP" if readiness >= 70 else "EKONOMIN RÄCKER INTE ÄN"
        primary = f"Närmaste ekonomiska spärr: {_format_gap(gaps[0])}."
    else:
        status = "GRANSKA"
        primary = "Kortet når inte KÖP, men ingen enskild standardspärr förklarar hela utfallet. Öppna full analys."

    return {
        "readiness_score": readiness,
        "status": status,
        "primary_action": primary,
        "blockers": blockers,
        "threshold_gaps": gaps,
        "next_steps": next_steps[:5],
        "safe_for_valuation": False,
        "note": "Köpberedskap förklarar befintlig analys och ändrar aldrig värdering, ranking, maxbud eller köpbeslut.",
    }
