"""Conservative Ending Soon opportunity classification.

The module never invents end times, valuation or max bids. It only prioritises
already analysed auction listings when the remaining time can be parsed from
listing-detail evidence and the current total cost is still below an existing
safe ceiling.
"""

from __future__ import annotations

import re


def parse_remaining_minutes(exact_end_text):
    """Parse only explicit relative Swedish/English remaining-time text.

    Returns None when the wording is ambiguous. We deliberately avoid guessing
    absolute dates/timezones here.
    """
    text = " ".join(str(exact_end_text or "").lower().split())
    if not text:
        return None

    days = hours = minutes = 0
    matched = False

    patterns = [
        (r"(\d+)\s*(?:dag|dagar|d)\b", "days"),
        (r"(\d+)\s*(?:tim|timmar|timme|h|hour|hours)\b", "hours"),
        (r"(\d+)\s*(?:min|minuter|minut|minute|minutes)\b", "minutes"),
    ]
    for pattern, unit in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            continue
        matched = True
        value = int(m.group(1))
        if unit == "days":
            days = value
        elif unit == "hours":
            hours = value
        else:
            minutes = value

    if not matched:
        return None
    return days * 1440 + hours * 60 + minutes


def build_ending_soon_opportunity(result, max_minutes=360):
    result = result or {}
    if str(result.get("sale_type") or "") != "Auktion":
        return {"eligible": False, "score": 0, "label": "Inte auktion", "reasons": []}

    remaining = parse_remaining_minutes(result.get("exact_end_text"))
    if remaining is None:
        return {
            "eligible": False,
            "score": 0,
            "label": "Sluttid ej säkert tolkad",
            "reasons": [],
            "blockers": ["saknar säkert tolkningsbar återstående tid"],
        }

    cost = float(result.get("total_cost") or 0)
    max_total = float(result.get("dynamic_max_total_price") or result.get("max_total_price") or 0)
    valuation = float(result.get("valuation_confidence_score") or 0)
    identity = float(result.get("exact_identity_gate_score") or 0)
    risk = float(result.get("risk_score") or 100)
    sold = int(result.get("sold_comparable_count") or 0)
    gate_ok = bool(result.get("exact_identity_gate_supports_dynamic_max_bid"))
    conflict = bool(result.get("detail_evidence_fusion_has_conflict")) or bool(result.get("identity_conflicts"))
    is_lot = bool(result.get("is_lot"))

    blockers = []
    if remaining < 0 or remaining > int(max_minutes):
        blockers.append(f"mer än {int(max_minutes // 60)} timmar kvar")
    if cost <= 0:
        blockers.append("saknar användbart totalpris")
    if max_total <= 0:
        blockers.append("saknar befintligt säkert maxbud")
    elif cost > max_total:
        blockers.append("aktuellt totalpris är över säkert maxbud")
    if valuation < 60:
        blockers.append("värderingssäkerhet under 60")
    if sold < 2:
        blockers.append("färre än 2 verifierade sold comps")
    if not gate_ok:
        blockers.append("identiteten är inte tillräckligt säker för maxbud")
    if conflict:
        blockers.append("identitetskonflikt finns")
    if is_lot:
        blockers.append("lot-annons")

    headroom = 0.0
    if max_total > 0 and cost >= 0:
        headroom = max(0.0, (max_total - cost) / max_total * 100.0)

    score = 0
    if not blockers:
        urgency = max(0.0, min(100.0, (int(max_minutes) - remaining) / max(1, int(max_minutes)) * 100.0))
        score = round(
            urgency * 0.28
            + min(100.0, headroom * 2.5) * 0.24
            + min(100.0, valuation) * 0.18
            + min(100.0, identity) * 0.16
            + min(100.0, max(0.0, 100.0 - risk)) * 0.14
        )
        score = int(max(0, min(100, score)))

    if score >= 80:
        label = "SLUTAR SNART – AGERA"
    elif score >= 65:
        label = "SLUTAR SNART – BEVAKA"
    elif score > 0:
        label = "NÄRA SLUTET"
    else:
        label = "EJ KVALIFICERAD"

    reasons = []
    if not blockers:
        reasons.append(f"ca {remaining} min kvar enligt annonsens detaljtext")
        reasons.append(f"aktuellt totalpris ligger {headroom:.0f} % under befintligt säkert maxbud")
        reasons.append(f"{sold} verifierade sold comps • värderingssäkerhet {valuation:.0f}/100")

    return {
        "eligible": not blockers,
        "score": score,
        "label": label,
        "remaining_minutes": remaining,
        "headroom_pct": round(headroom, 1),
        "blockers": blockers,
        "reasons": reasons,
        "safe_for_valuation": False,
        "note": "Ending Soon Hunter skapar aldrig sluttid, värde eller maxbud; den prioriterar endast befintlig verifierad analys.",
    }
