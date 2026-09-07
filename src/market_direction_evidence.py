"""Evidence strength dimensions for Comp Market Direction.

No synthetic confidence score and no new valuation/buy thresholds. Reports only
observable support: sample size, time span, dated coverage and directional
agreement.
"""
from src.comp_market_direction import build_comp_market_direction

def build_market_direction_evidence(exact_rows):
    d=build_comp_market_direction(exact_rows)
    if d.get("status")!="DESCRIBED":
        return {"status":"INSUFFICIENT_DATA","direction_status":d.get("status"),
                "note":"Riktningens evidens kan inte bedömas utan minst två daterade prissatta Exact-comps."}
    count=int(d.get("count") or 0)
    moves=max(0,count-1)
    up=int(d.get("up_moves") or 0); down=int(d.get("down_moves") or 0); flat=int(d.get("flat_moves") or 0)
    dominant=max(up,down,flat) if moves else 0
    agreement=(dominant/moves) if moves else None
    from datetime import date
    try:
        first=date.fromisoformat(d["first_date"]); latest=date.fromisoformat(d["latest_date"])
        span=(latest-first).days
    except Exception:
        span=None
    missing_dates=int(d.get("missing_date_count") or 0)
    missing_prices=int(d.get("missing_price_count") or 0)
    observed=count+missing_dates+missing_prices
    dated_coverage=(count/observed) if observed else None
    return {
      "status":"DESCRIBED","exact_count":count,"move_count":moves,"span_days":span,
      "up_moves":up,"down_moves":down,"flat_moves":flat,
      "dominant_move_share":round(agreement,3) if agreement is not None else None,
      "dated_priced_coverage":round(dated_coverage,3) if dated_coverage is not None else None,
      "missing_date_count":missing_dates,"missing_price_count":missing_prices,
      "unanimous_direction": bool(moves and (up==moves or down==moves or flat==moves)),
      "note":"Ingen sammanslagen confidence score. Styrkan visas som observerbara dimensioner så att 2 försäljningar över lång tid inte ser likvärdiga ut med många täta observationer."
    }
