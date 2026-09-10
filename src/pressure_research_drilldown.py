"""Pressure Research Drilldown.

Explains why one exact-card identity appears in Pressure Research, shows the
verified exact SOLD evidence supporting the observation, and lists explicit
existing blockers before the listing may even be considered decision-ready.
It never upgrades a decision or creates new economics.
"""
from __future__ import annotations

from src.market_pressure_monitor import exact_sold_price_series, build_market_pressure_monitor
from src.exact_supply_history import history_for_target
from src.exact_identity_gate import build_exact_identity_gate


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _is_buy(item):
    d=str((item or {}).get("decision") or (item or {}).get("recommendation") or "").upper()
    return d.startswith("KÖP") or d.startswith("KOP")


def build_pressure_drilldown(item, supply_history_rows, sold_records):
    item=dict(item or {})
    pressure=build_market_pressure_monitor(item,supply_history_rows,sold_records)
    identity=build_exact_identity_gate(item)
    history=history_for_target(item,supply_history_rows)
    sold_series=exact_sold_price_series(item,supply_history_rows,sold_records)

    why=[]
    if pressure.get("supply_direction")=="MINSKAT_OBSERVERAT_UTBUD":
        why.append({
            "kind":"SUPPLY_DOWN",
            "text":f"Observerat bekräftat exact-supply förändrades {int(pressure.get('supply_change') or 0):+d}.",
        })
    if int(pressure.get("exact_sold_with_price_in_window") or 0)>0:
        why.append({
            "kind":"VERIFIED_SOLD",
            "text":f"{int(pressure.get('exact_sold_with_price_in_window') or 0)} verifierade exakta SOLD med pris finns i supply-perioden.",
        })
    if pressure.get("price_direction")=="HÖGRE_OBSERVERAT_SOLD_PRIS":
        early=pressure.get("early_median_sek")
        late=pressure.get("late_median_sek")
        why.append({
            "kind":"PRICE_UP",
            "text":f"Observerad SOLD-median steg från {early:.0f} till {late:.0f} kr.",
        })

    sold_evidence=[]
    for row in (sold_series.get("rows") or []):
        sold_evidence.append({
            "sold_at":row.get("sold_at"),
            "price_sek":row.get("price_sek"),
        })

    blockers=[]
    if not identity.get("supports_exact_comp_search"):
        blockers.append("Exakt kortidentitet räcker inte för exact-comp-sökning.")
    if not identity.get("supports_dynamic_max_bid"):
        blockers.append("Identiteten är inte tillräckligt stark för dynamiskt maxbud.")
    sold_count=int(item.get("sold_comparable_count") or 0)
    if sold_count<2:
        blockers.append("Minst två matchande verifierade sålda jämförelseobjekt saknas.")
    if not bool(item.get("valuation_display_safe")):
        blockers.append("Marknadsvärdet är inte säkert nog för visning.")
    valuation_conf=_num(item.get("valuation_confidence_score"),0)
    if valuation_conf<60:
        blockers.append(f"Värderingssäkerheten är för låg ({valuation_conf:.0f}/100).")
    if not _is_buy(item):
        existing=str(item.get("decision") or item.get("recommendation") or "Ingen KÖP-status")
        blockers.append(f"Befintligt beslut är {existing}; Pressure Research får inte uppgradera detta.")
    if item.get("max_item_price") in (None,"") and item.get("max_total_price") in (None,""):
        blockers.append("Inget säkert maxpris finns tillgängligt.")

    return {
        "ready":bool(identity.get("supports_exact_comp_search")),
        "why":why,
        "supply_snapshots":[
            {
                "observed_at":r.get("observed_at"),
                "confirmed_exact":int(r.get("confirmed_exact") or 0),
                "possible":int(r.get("possible") or 0),
                "wrong_card":int(r.get("wrong_card") or 0),
            }
            for r in history
        ],
        "sold_evidence":sold_evidence,
        "blockers_before_buy_consideration":blockers,
        "pressure_status":pressure.get("status"),
        "pressure_observation":pressure.get("observation"),
        "current_decision":item.get("decision") or item.get("recommendation"),
        "valuation_display_safe":bool(item.get("valuation_display_safe")),
        "sold_comparable_count":sold_count,
        "identity_status":identity.get("status"),
        "creates_new_score":False,
        "creates_demand_signal":False,
        "creates_scarcity_score":False,
        "creates_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
        "note":"Drilldown förklarar befintligt underlag. Frånvaro av blockerare är inte samma sak som KÖP.",
    }
