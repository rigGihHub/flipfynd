"""Pressure Research Queue.

Surfaces exact-card identities whose already-observed Market Pressure facts are
especially worth manual research. It never creates a BUY decision, valuation,
max price, demand signal, scarcity score or synthetic opportunity score.
"""
from __future__ import annotations

from src.exact_card_supply import exact_identity_key
from src.market_pressure_monitor import build_market_pressure_monitor


def _label_for(pressure):
    supply_down = pressure.get("supply_direction") == "MINSKAT_OBSERVERAT_UTBUD"
    sold_present = int(pressure.get("exact_sold_with_price_in_window") or 0) > 0
    price_up = pressure.get("price_direction") == "HÖGRE_OBSERVERAT_SOLD_PRIS"
    evidence_count = sum((supply_down, sold_present, price_up))

    if supply_down and sold_present and price_up:
        status = "PRIORITERA_RESEARCH"
        label = "Tre observerade trycksignaler – prioritera manuell research"
    elif evidence_count >= 2:
        status = "RESEARCH"
        label = "Två observerade trycksignaler – värd manuell research"
    else:
        status = "SVAGT_UNDERLAG"
        label = "För svagt kombinerat underlag"

    return {
        "status": status,
        "label": label,
        "evidence_count": evidence_count,
        "supply_down": supply_down,
        "verified_sold_present": sold_present,
        "observed_sold_price_up": price_up,
    }


def build_pressure_research_row(item, supply_history_rows, sold_records):
    key = exact_identity_key(item or {})
    if key is None:
        return {
            "eligible": False,
            "status": "IDENTITY_NOT_READY",
            "creates_buy_decision": False,
            "creates_value": False,
        }

    pressure = build_market_pressure_monitor(item, supply_history_rows, sold_records)
    labels = _label_for(pressure)
    eligible = labels["status"] in {"PRIORITERA_RESEARCH", "RESEARCH"}
    return {
        "eligible": eligible,
        "identity_key": key,
        "title": item.get("titel") or item.get("title") or "",
        "player_name": item.get("player_name"),
        "set_name": item.get("set_name") or item.get("card_set"),
        "season": item.get("season") or item.get("year"),
        "card_number": item.get("card_number") or item.get("checklist_number"),
        **labels,
        "supply_direction": pressure.get("supply_direction"),
        "supply_change": pressure.get("supply_change"),
        "exact_sold_with_price_in_window": pressure.get("exact_sold_with_price_in_window", 0),
        "price_direction": pressure.get("price_direction"),
        "early_median_sek": pressure.get("early_median_sek"),
        "late_median_sek": pressure.get("late_median_sek"),
        "price_change_sek": pressure.get("price_change_sek"),
        "pressure_status": pressure.get("status"),
        "creates_demand_signal": False,
        "creates_scarcity_score": False,
        "creates_market_trend": False,
        "creates_value": False,
        "creates_buy_decision": False,
        "creates_max_price": False,
        "note": (
            "Kön prioriterar bara manuell research utifrån redan observerade fakta. "
            "Den är inte en KÖP-lista och bevisar inte efterfrågan, knapphet eller undervärdering."
        ),
    }


def build_pressure_research_queue(items, supply_history_rows, sold_records, *, limit=8):
    rows = []
    seen = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        row = build_pressure_research_row(item, supply_history_rows, sold_records)
        if not row.get("eligible"):
            continue
        key = row.get("identity_key")
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)

    # This is evidence ordering, not an opportunity score: full three-condition
    # rows first, then two-condition rows. Existing price/supply magnitudes are
    # only deterministic tie-breakers and never change eligibility.
    rows.sort(
        key=lambda r: (
            int(r.get("evidence_count") or 0),
            int(r.get("exact_sold_with_price_in_window") or 0),
            abs(float(r.get("supply_change") or 0)),
        ),
        reverse=True,
    )
    rows = rows[:max(0, int(limit))]
    return {
        "rows": rows,
        "count": len(rows),
        "priority_count": sum(1 for r in rows if r.get("status") == "PRIORITERA_RESEARCH"),
        "creates_new_score": False,
        "creates_buy_decision": False,
        "creates_value": False,
        "creates_demand_signal": False,
        "note": "Pressure Research Queue är endast en manuell researchkö.",
    }
