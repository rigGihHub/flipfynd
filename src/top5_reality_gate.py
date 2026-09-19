"""Final economic reality gate for Top 5 candidates.

The gate may demote/reject a research candidate. It never invents value and
never upgrades UNDERSÖK to KÖP.
"""
from __future__ import annotations


def _n(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def apply_reality_gate(row):
    row = dict(row or {})
    total = _n(row.get("total_cost"))
    market = _n(row.get("market_value"))
    asking = _n(row.get("asking_reference"))
    sold = int(_n(row.get("sold_comps"), 0) or 0)
    decision = str(row.get("decision") or "UNDERSÖK").upper()
    reasons = list(row.get("reasons") or [])
    flags = []
    penalty = 0.0

    if total is None:
        flags.append("total köpkostnad saknas")
        penalty += 25
    if market is None and sold < 2:
        flags.append("saknar verifierat återförsäljningsvärde")
        penalty += 12

    # Active asking prices are negative/context evidence only. A candidate
    # cannot look economically attractive when acquisition already consumes
    # most/all of the cheapest observed comparable asking price.
    if total is not None and asking is not None and asking > 0:
        ratio = total / asking
        if ratio >= 1.0:
            flags.append("köpkostnad är minst lika hög som observerat asking-pris")
            penalty += min(35, 20 + (ratio - 1) * 12)
        elif ratio >= 0.80:
            flags.append("för liten marginal mot observerat asking-pris")
            penalty += 14
        elif ratio >= 0.65:
            flags.append("tunn marginal mot observerat asking-pris")
            penalty += 7

    # A safe market value can support economics; asking data cannot.
    verified_profit = None
    if total is not None and market is not None:
        verified_profit = market - total
        if verified_profit <= 0:
            flags.append("verifierat värde överstiger inte köpkostnaden")
            penalty += 35

    if decision == "KÖP":
        if sold < 2 or market is None or verified_profit is None or verified_profit <= 0:
            decision = "UNDERSÖK"
            flags.append("KÖP-gaten saknar tillräcklig ekonomisk evidens")

    score = max(0.0, float(row.get("potential") or 0) - penalty)
    row["decision"] = decision
    row["potential"] = round(score, 1)
    row["reality_gate_penalty"] = round(penalty, 1)
    row["reality_gate_flags"] = list(dict.fromkeys(flags))
    row["verified_gross_edge"] = verified_profit
    if flags:
        reasons.extend(flags[:3])
    row["reasons"] = list(dict.fromkeys(reasons))[:6]
    if decision != "KÖP" and flags:
        row["primary_blocker"] = flags[0]
    return row


def gate_and_sort(rows, limit=5):
    gated = [apply_reality_gate(row) for row in (rows or [])]
    gated.sort(key=lambda r: (
        str(r.get("decision") or "").upper() == "KÖP",
        -float(r.get("reality_gate_penalty") or 0),
        float(r.get("potential") or 0),
        float(r.get("certainty") or 0),
        float(r.get("freshness_score") or 0),
    ), reverse=True)
    return gated[:max(0, int(limit))]
