"""Decision Confidence Audit for FlipFynd.

This module checks whether a clear KÖP decision is supported by sufficiently
strong evidence. It never creates a value, profit estimate, or opportunity
signal. Its only allowed directional effect is to downgrade a clear buy to
KANSKE when the supporting evidence is too thin.
"""
from __future__ import annotations

from typing import Any

BUY_DECISIONS = {"KÖP", "KÖP (starkt fynd)"}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def audit_decision_confidence(
    *,
    decision: str,
    valuation_confidence_score: float,
    identity_confidence_score: float,
    deal_confidence_score: float,
    listing_quality_score: float,
    risk_score: float,
    player_match_confidence: str,
    comp_valuation_basis: str = "none",
    sold_comparable_count: int = 0,
    asking_comparable_count: int = 0,
    exact_identity_gate_status: str | None = None,
    valuation_display_safe: bool = True,
    is_lot: bool = False,
    extreme_discount: bool = False,
) -> dict[str, Any]:
    """Audit whether a clear buy has decision-grade supporting evidence.

    Thresholds are deliberately modest: the audit is a final safety backstop,
    not a replacement valuation model. Weak evidence can only downgrade a buy;
    the audit can never upgrade KANSKE/SKIP to KÖP.
    """
    raw_decision = str(decision or "SKIP")
    valuation = max(0.0, min(100.0, _num(valuation_confidence_score)))
    identity = max(0.0, min(100.0, _num(identity_confidence_score)))
    deal = max(0.0, min(100.0, _num(deal_confidence_score)))
    listing = max(0.0, min(100.0, _num(listing_quality_score)))
    risk = max(0.0, min(100.0, _num(risk_score)))
    player_conf = str(player_match_confidence or "low").casefold()
    basis = str(comp_valuation_basis or "none").casefold()
    gate_status = str(exact_identity_gate_status or "").upper()
    sold_count = max(0, int(sold_comparable_count or 0))
    asking_count = max(0, int(asking_comparable_count or 0))

    blockers: list[str] = []
    warnings: list[str] = []
    strengths: list[str] = []

    # Clear buys need at least a minimally decision-grade price basis. In
    # particular, heuristic-only value must not silently support a KÖP badge.
    if valuation < 35:
        blockers.append(f"värderingssäkerheten är bara {valuation:.0f}/100")
    elif valuation < 50:
        warnings.append(f"värderingssäkerheten är begränsad ({valuation:.0f}/100)")
    else:
        strengths.append(f"värderingssäkerhet {valuation:.0f}/100")

    if identity < 50:
        blockers.append(f"kortidentiteten är för osäker ({identity:.0f}/100)")
    elif identity < 70:
        warnings.append(f"kortidentiteten är inte fullt robust ({identity:.0f}/100)")
    else:
        strengths.append(f"identitet {identity:.0f}/100")

    if deal < 40:
        blockers.append(f"samlad fyndsäkerhet är för låg ({deal:.0f}/100)")
    elif deal < 55:
        warnings.append(f"samlad fyndsäkerhet är måttlig ({deal:.0f}/100)")

    if listing < 45:
        blockers.append(f"annonsunderlaget är för svagt ({listing:.0f}/100)")
    elif listing < 60:
        warnings.append(f"annonsunderlaget är begränsat ({listing:.0f}/100)")

    if player_conf == "low":
        blockers.append("spelaren är inte identifierad tillräckligt säkert")

    if risk >= 75:
        blockers.append(f"risknivån är för hög ({risk:.0f}/100)")
    elif risk > 60:
        warnings.append(f"risknivån är förhöjd ({risk:.0f}/100)")

    if not valuation_display_safe:
        blockers.append("värdet är inte säkert att visa för den här premiumidentiteten")

    if is_lot:
        blockers.append("lot/multipack saknar säker enkelkortsekonomi")

    if extreme_discount:
        warnings.append("extrem prisavvikelse kräver extra verifiering")

    # Asking prices may inform research but are weaker than sold evidence. We
    # do not block them categorically, but a buy based only on asking comps must
    # have clearly above-minimum valuation confidence.
    if basis == "sold":
        if sold_count < 2:
            blockers.append("för få verifierade sålda comps för sold-baserad värdering")
        else:
            strengths.append(f"{sold_count} verifierade sålda comps")
    elif basis in {"asking", "current", "current_listings", "listings"}:
        if valuation < 55 or asking_count < 3:
            blockers.append("aktiva annonser ger inte tillräckligt starkt prisstöd för ett klart KÖP")
        else:
            warnings.append("prisstödet bygger främst på begärda priser, inte avslut")
    elif basis == "none":
        if valuation < 50:
            # Usually catches heuristic-only valuations, which start very low.
            blockers.append("värderingen saknar tillräckligt marknadsunderlag")
        else:
            warnings.append("värderingen saknar verifierade marknadscomps")

    if gate_status == "LÅST" and identity < 70:
        warnings.append("Exact Identity Gate är låst")

    # De-duplicate while preserving order.
    blockers = list(dict.fromkeys(blockers))
    warnings = [x for x in dict.fromkeys(warnings) if x not in blockers]
    strengths = list(dict.fromkeys(strengths))

    audited_decision = raw_decision
    downgraded = False
    if raw_decision in BUY_DECISIONS and blockers:
        audited_decision = "KANSKE"
        downgraded = True

    if blockers:
        status = "BLOCKERAD"
        label = "KÖP kräver mer bevis"
    elif warnings:
        status = "GRANSKA"
        label = "Beslutet har godtagbart men inte optimalt stöd"
    else:
        status = "BESLUTSSTARK"
        label = "Beslutet har tillräckligt stöd"

    # Transparent diagnostic score only; it never feeds valuation/ranking.
    score = round(
        max(
            0.0,
            min(
                100.0,
                valuation * 0.30
                + identity * 0.25
                + deal * 0.20
                + listing * 0.10
                + (100.0 - risk) * 0.15,
            ),
        )
    )

    price_evidence_blocked = any(
        phrase in blocker
        for blocker in blockers
        for phrase in (
            "värderingssäkerheten",
            "marknadsunderlag",
            "aktiva annonser",
            "sålda comps",
            "värdet är inte säkert",
        )
    )

    return {
        "status": status,
        "label": label,
        "score": int(score),
        "original_decision": raw_decision,
        "audited_decision": audited_decision,
        "downgraded": downgraded,
        "blockers": blockers,
        "warnings": warnings,
        "strengths": strengths,
        "thin_value_evidence": price_evidence_blocked,
        "allow_max_purchase": not price_evidence_blocked and not is_lot,
        "automatic_weight_changes": False,
        "note": (
            "Decision Confidence Audit skapar inga värden och kan aldrig uppgradera ett beslut. "
            "Den kan bara stoppa ett tydligt KÖP när stöddata är för tunn."
        ),
    }
