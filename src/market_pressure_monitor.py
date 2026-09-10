"""Market Pressure Monitor.

Descriptive side-by-side view of exact active supply, verified exact SOLD count
and realised exact SOLD prices for one structured card identity. It never turns
those observations into a demand signal, scarcity score, valuation or BUY.
"""
from __future__ import annotations
from datetime import datetime
from statistics import median

from src.exact_supply_history import history_for_target, summarize_history
from src.supply_vs_sales_monitor import exact_verified_sold_matches


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


def _price_sek(row):
    """Imported verified SOLD prices are normalized to SEK upstream."""
    for field in ("sold_total_price","sold_price"):
        value=(row or {}).get(field)
        try:
            num=float(value)
        except (TypeError,ValueError):
            continue
        if num>0:
            return num
    return None


def exact_sold_price_series(target, supply_history_rows, sold_records):
    history=history_for_target(target,supply_history_rows)
    if len(history)<2:
        return {"status":"OTILLRÄCKLIG_SUPPLY_HISTORIK","rows":[],"count":0}
    start=_parse_dt(history[0].get("observed_at"))
    end=_parse_dt(history[-1].get("observed_at"))
    if not start or not end:
        return {"status":"OGILTIGA_TIDSTÄMPLAR","rows":[],"count":0}
    if end<start:
        start,end=end,start

    rows=[]
    undated=0
    unpriced=0
    for sold in exact_verified_sold_matches(target,sold_records):
        dt=_parse_dt(sold.get("sold_at"))
        if dt is None:
            undated += 1
            continue
        try:
            inside=start <= dt <= end
        except TypeError:
            inside=False
        if not inside:
            continue
        price=_price_sek(sold)
        if price is None:
            unpriced += 1
            continue
        rows.append({"sold_at":sold.get("sold_at"),"dt":dt,"price_sek":round(price,2)})
    rows.sort(key=lambda r:r["dt"])
    return {
        "status":"OK",
        "rows":rows,
        "count":len(rows),
        "undated_exact_sold":undated,
        "unpriced_exact_sold":unpriced,
        "window_start":history[0].get("observed_at"),
        "window_end":history[-1].get("observed_at"),
    }


def summarize_realised_price_direction(target, supply_history_rows, sold_records, *, minimum_sales=3):
    series=exact_sold_price_series(target,supply_history_rows,sold_records)
    rows=series.get("rows") or []
    minimum=max(3,int(minimum_sales))
    if series.get("status")!="OK" or len(rows)<minimum:
        return {
            "status":"OTILLRÄCKLIG_PRISHISTORIK",
            "sales_with_price":len(rows),
            "minimum_sales":minimum,
            "direction":"EJ_BEDÖMBAR",
            "creates_market_trend":False,
        }

    split=max(1,len(rows)//2)
    early=[r["price_sek"] for r in rows[:split]]
    late=[r["price_sek"] for r in rows[split:]]
    early_median=round(float(median(early)),2)
    late_median=round(float(median(late)),2)
    change=round(late_median-early_median,2)
    if change>0:
        direction="HÖGRE_OBSERVERAT_SOLD_PRIS"
    elif change<0:
        direction="LÄGRE_OBSERVERAT_SOLD_PRIS"
    else:
        direction="OFÖRÄNDRAT_OBSERVERAT_SOLD_PRIS"
    return {
        "status":"OK",
        "sales_with_price":len(rows),
        "direction":direction,
        "early_median_sek":early_median,
        "late_median_sek":late_median,
        "change_sek":change,
        "creates_market_trend":False,
        "note":"Prisriktningen jämför medianen i tidigare och senare verifierade exakta SOLD inom supply-perioden; den är inte en generell marknadstrend.",
    }


def build_market_pressure_monitor(target, supply_history_rows, sold_records):
    supply=summarize_history(target,supply_history_rows)
    prices=summarize_realised_price_direction(target,supply_history_rows,sold_records)
    series=exact_sold_price_series(target,supply_history_rows,sold_records)

    if supply.get("status")!="OK":
        status="OTILLRÄCKLIG_HISTORIK"
        observation="För få exact-supply-observationer för Market Pressure Monitor."
    else:
        sold_count=series.get("count",0) if series.get("status")=="OK" else 0
        supply_direction=supply.get("direction")
        price_direction=prices.get("direction")
        if prices.get("status")!="OK":
            status="SUPPLY_OCH_SOLD_OBSERVERAT"
            observation=(
                f"Supply-riktning: {supply_direction}. {sold_count} verifierade exakta SOLD med pris "
                "finns i perioden, men prisunderlaget är för tunt för prisriktning."
            )
        else:
            status="TRE_SERIER_OBSERVERADE"
            observation=(
                f"Supply-riktning: {supply_direction}. Verifierade exakta SOLD med pris i perioden: {sold_count}. "
                f"Observerad SOLD-prisriktning: {price_direction}."
            )

    return {
        "status":status,
        "supply_direction":supply.get("direction"),
        "supply_change":supply.get("change"),
        "supply_snapshots":supply.get("snapshots",0),
        "exact_sold_with_price_in_window":series.get("count",0),
        "price_direction":prices.get("direction"),
        "early_median_sek":prices.get("early_median_sek"),
        "late_median_sek":prices.get("late_median_sek"),
        "price_change_sek":prices.get("change_sek"),
        "observation":observation,
        "creates_demand_signal":False,
        "creates_scarcity_score":False,
        "creates_market_trend":False,
        "creates_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
        "note":"Market Pressure Monitor visar observerade fakta sida vid sida. Kombinationen är inte i sig bevis för efterfrågan, knapphet, undervärdering eller köpbarhet.",
    }
