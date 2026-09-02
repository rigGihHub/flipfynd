"""Conservative Buy-Now opportunity classification.

This module never creates valuation. It only prioritises already analysed
listings when existing evidence is strong enough.
"""


def build_buy_now_opportunity(result):
    result = result or {}
    if str(result.get("sale_type") or "") != "Köp nu":
        return {"eligible": False, "score": 0, "label": "Inte Köp nu", "reasons": []}

    cost = float(result.get("total_cost") or 0)
    value = float(result.get("expected_resale") or result.get("market_value") or 0)
    net = float(result.get("net_profit_estimate") or 0)
    roi_raw = float(result.get("roi_estimate") or 0)
    roi_pct = roi_raw * 100 if abs(roi_raw) <= 5 else roi_raw
    valuation = float(result.get("valuation_confidence_score") or 0)
    identity = float(result.get("exact_identity_gate_score") or 0)
    risk = float(result.get("risk_score") or 100)
    sold = int(result.get("sold_comparable_count") or 0)
    gate_ok = bool(result.get("exact_identity_gate_supports_exact_comp_search"))
    conflict = bool(result.get("detail_evidence_fusion_has_conflict")) or bool(result.get("identity_conflicts"))
    is_lot = bool(result.get("is_lot"))

    blockers = []
    if cost <= 0:
        blockers.append("saknar användbart totalpris")
    if valuation < 60:
        blockers.append("värderingssäkerhet under 60")
    if sold < 2:
        blockers.append("färre än 2 verifierade sold comps")
    if not gate_ok:
        blockers.append("identiteten är inte tillräckligt säker för exakt comp-sökning")
    if conflict:
        blockers.append("identitetskonflikt finns")
    if is_lot:
        blockers.append("lot-annons")
    if net < 30:
        blockers.append("förväntad nettovinst under 30 kr")
    if roi_pct < 18:
        blockers.append("förväntad ROI under 18 %")

    discount_pct = 0.0
    if value > 0 and cost > 0:
        discount_pct = max(-100.0, min(95.0, (value - cost) / value * 100.0))

    score = 0.0
    if not blockers:
        score = (
            min(100.0, max(0.0, discount_pct * 2.0)) * 0.24
            + min(100.0, max(0.0, net / 2.0)) * 0.20
            + min(100.0, max(0.0, roi_pct)) * 0.18
            + min(100.0, valuation) * 0.16
            + min(100.0, identity) * 0.12
            + min(100.0, max(0.0, 100.0 - risk)) * 0.10
        )
        score = round(max(0.0, min(100.0, score)))

    if score >= 80:
        label = "AGERA NU"
    elif score >= 65:
        label = "STARK KÖP NU-KANDIDAT"
    elif score > 0:
        label = "BEVAKA"
    else:
        label = "EJ KVALIFICERAD"

    reasons = []
    if not blockers:
        reasons.append(f"Köp nu-pris med {discount_pct:.0f} % gap mot befintligt försiktigt värde")
        reasons.append(f"Förväntad nettovinst {net:.0f} kr och ROI {roi_pct:.0f} %")
        reasons.append(f"{sold} verifierade sold comps • värderingssäkerhet {valuation:.0f}/100")

    return {
        "eligible": not blockers,
        "score": int(score),
        "label": label,
        "discount_pct": round(discount_pct, 1),
        "blockers": blockers,
        "reasons": reasons,
        "safe_for_valuation": False,
        "note": "Buy-Now Hunter skapar aldrig värde eller maxbud; den prioriterar endast befintlig analys.",
    }
