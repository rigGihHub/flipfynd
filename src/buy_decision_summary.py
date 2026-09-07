"""Compact buy-decision summary for already approved top buys."""
def _n(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def build_buy_decision_summary(queue, candidates):
    by_title={str(x.get("titel") or ""):x for x in (candidates or [])}
    rows=[]
    for pick in (queue or {}).get("picks", []):
        item=by_title.get(str(pick.get("title") or ""))
        if not item:
            continue
        total=_n(item.get("analysis_total_cost") or item.get("total_cost"))
        max_total=_n(item.get("max_total_price"))
        likely=_n(item.get("net_profit_estimate"))
        downside=_n(item.get("floor_profit_estimate"))
        days=_n(item.get("flip_velocity_expected_days")) if item.get("flip_velocity_evidence") == "verified_sold_velocity" else None
        if total in (None,0) or likely is None:
            continue
        rows.append({
            "rank":pick.get("rank"),
            "title":pick.get("title"),
            "buy_total":total,
            "max_total":max_total,
            "likely_profit":likely,
            "downside_profit":downside,
            "expected_days":days,
            "velocity_verified":days is not None,
            "url":item.get("lank"),
        })
    return {
        "status":"READY" if rows else "INSUFFICIENT_DATA",
        "rows":rows,
        "note":"Sammanfattningen använder bara redan beräknade köp-, vinst-, nedsides- och säljtidsvärden. Den skapar inga nya antaganden."
    }
