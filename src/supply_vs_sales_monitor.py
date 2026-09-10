"""Supply vs Sales Monitor.

Combines Exact Supply History with verified exact SOLD records for the same
structured card identity. Descriptive only: no demand inference, scarcity score,
valuation, max price or BUY decision.
"""
from __future__ import annotations
from datetime import datetime

from src.exact_card_supply import exact_identity_key
from src.exact_supply_history import history_for_target, summarize_history
from src.sold_comp_intake import review_sold_comp_intake


def _clean(v):
    return " ".join(str(v or "").split()).strip().casefold()


def _target_identity(target):
    key=exact_identity_key(target)
    if key is None:
        return None
    return key


def _sold_key(record):
    review=review_sold_comp_intake(record or {})
    if not review.get("exact_identity_ready"):
        return None
    ident=review.get("identity") or {}
    key=(
        _clean(ident.get("player_name")),
        _clean(ident.get("set_name")),
        _clean(ident.get("season")),
        _clean(ident.get("card_number")),
        _clean(ident.get("parallel")),
        _clean(ident.get("grading_company")),
        _clean(ident.get("grade")),
    )
    if not all(key[:4]):
        return None
    return key


def exact_verified_sold_matches(target, sold_records):
    target_key=_target_identity(target)
    if target_key is None:
        return []
    out=[]
    for row in sold_records or []:
        if not isinstance(row,dict):
            continue
        if _sold_key(row)==target_key:
            out.append(row)
    return out


def _parse_dt(value):
    text=str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z","+00:00"))
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10])
        except ValueError:
            return None


def sold_during_supply_window(target, supply_history_rows, sold_records):
    history=history_for_target(target,supply_history_rows)
    if len(history)<2:
        return {
            "status":"OTILLRÄCKLIG_SUPPLY_HISTORIK",
            "window_sold_count":None,
            "exact_verified_sold_total":len(exact_verified_sold_matches(target,sold_records)),
        }
    start=_parse_dt(history[0].get("observed_at"))
    end=_parse_dt(history[-1].get("observed_at"))
    if not start or not end:
        return {
            "status":"OGILTIGA_TIDSTÄMPLAR",
            "window_sold_count":None,
            "exact_verified_sold_total":len(exact_verified_sold_matches(target,sold_records)),
        }
    if end < start:
        start,end=end,start

    matches=exact_verified_sold_matches(target,sold_records)
    in_window=[]
    undated=0
    for row in matches:
        dt=_parse_dt(row.get("sold_at"))
        if dt is None:
            undated += 1
            continue
        try:
            inside=start <= dt <= end
        except TypeError:
            # Mixed timezone-aware/naive timestamps cannot be compared safely.
            inside=False
        if inside:
            in_window.append(row)

    return {
        "status":"OK",
        "window_start":history[0].get("observed_at"),
        "window_end":history[-1].get("observed_at"),
        "window_sold_count":len(in_window),
        "exact_verified_sold_total":len(matches),
        "exact_verified_sold_undated":undated,
    }


def build_supply_vs_sales_monitor(target, supply_history_rows, sold_records):
    supply=summarize_history(target,supply_history_rows)
    sales=sold_during_supply_window(target,supply_history_rows,sold_records)

    if supply.get("status")!="OK":
        status="OTILLRÄCKLIG_HISTORIK"
        observation="Supply-historiken är för tunn för jämförelse."
    elif sales.get("window_sold_count") is None:
        status="OTILLRÄCKLIG_TIDSEVIDENS"
        observation="Exakta verifierade SOLD kan inte jämföras säkert med supply-perioden."
    else:
        status="DESKRIPTIV_JÄMFÖRELSE"
        change=supply.get("change")
        sold_count=sales.get("window_sold_count",0)
        if change < 0 and sold_count > 0:
            observation="Observerat exact-supply minskade samtidigt som verifierade exakta försäljningar registrerades."
        elif change < 0:
            observation="Observerat exact-supply minskade, men inga verifierade exakta försäljningar finns registrerade i perioden."
        elif change > 0 and sold_count > 0:
            observation="Observerat exact-supply ökade samtidigt som verifierade exakta försäljningar registrerades."
        elif change > 0:
            observation="Observerat exact-supply ökade; inga verifierade exakta försäljningar finns registrerade i perioden."
        elif sold_count > 0:
            observation="Observerat exact-supply var oförändrat samtidigt som verifierade exakta försäljningar registrerades."
        else:
            observation="Observerat exact-supply var oförändrat och inga verifierade exakta försäljningar finns registrerade i perioden."

    return {
        "status":status,
        "supply_direction":supply.get("direction"),
        "supply_change":supply.get("change"),
        "supply_snapshots":supply.get("snapshots",0),
        "verified_exact_sold_in_window":sales.get("window_sold_count"),
        "verified_exact_sold_total":sales.get("exact_verified_sold_total",0),
        "verified_exact_sold_undated":sales.get("exact_verified_sold_undated",0),
        "observation":observation,
        "creates_demand_signal":False,
        "creates_scarcity_score":False,
        "creates_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
        "note":"Jämförelsen beskriver endast FlipFynds sparade supply-observationer och verifierade exakta SOLD-poster. Den bevisar inte efterfrågan eller undervärdering.",
    }
