"""Market Segment Coverage.

Broadens full analysis across budget-relative price bands and listing formats so
FlipFynd does not spend most of its expensive analysis on one repetitive slice
of the market (for example micro-priced single-card listings).

This changes only which already-fetched candidates receive full analysis. It
does not create a deal score, valuation, max price, risk or BUY decision.
"""
from __future__ import annotations


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def price_band(price, budget):
    price=_num(price)
    budget=_num(budget)
    if price is None or budget is None or budget <= 0:
        return "unknown"
    ratio=price/budget
    if ratio <= 0.05:
        return "micro"
    if ratio <= 0.20:
        return "low"
    if ratio <= 0.50:
        return "mid"
    return "upper"


def sale_type(item):
    item=item or {}
    explicit=str(
        item.get("sale_type")
        or item.get("listing_type")
        or item.get("annonsform")
        or ""
    ).casefold()
    if "köp nu" in explicit or "buy" in explicit:
        return "buy-now"
    if "auktion" in explicit or "auction" in explicit:
        return "auction"

    text=" ".join(str(item.get(k) or "") for k in ("titel","title","text","description")).casefold()
    if "köp nu" in text:
        return "buy-now"
    if "utropspris" in text or "ledande bud" in text or " auktion" in text:
        return "auction"
    return "unknown"


def object_type(fast):
    fast=fast or {}
    return "lot" if fast.get("is_lot") or fast.get("lot_count") else "single"


def segment_key(item, fast, budget):
    return (
        price_band((item or {}).get("pris"), budget),
        sale_type(item),
        object_type(fast),
    )


def add_segment_coverage_indices(
    candidates,
    selected_indices,
    *,
    budget,
    extra_slots=6,
    hard_cap=42,
    max_per_player=2,
):
    """Add candidates from segment combinations missing in current full analysis."""
    selected=list(dict.fromkeys(
        int(i) for i in (selected_indices or [])
        if 0 <= int(i) < len(candidates or [])
    ))
    selected_set=set(selected)
    room=max(0,int(hard_cap)-len(selected))
    take=min(max(0,int(extra_slots)),room)
    if take<=0:
        return selected, []

    represented=set()
    player_counts={}
    for idx in selected:
        item,fast,_att=candidates[idx]
        represented.add(segment_key(item,fast,budget))
        player=str((fast or {}).get("player_name") or f"__unknown_{idx}").casefold()
        player_counts[player]=player_counts.get(player,0)+1

    pool=[]
    for idx,(item,fast,_att) in enumerate(candidates or []):
        if idx in selected_set:
            continue
        seg=segment_key(item,fast,budget)
        if seg[0]=="unknown":
            continue
        player=str((fast or {}).get("player_name") or f"__unknown_{idx}").casefold()
        pool.append({
            "idx":idx,
            "segment":seg,
            "player":player,
            "rank":_num((fast or {}).get("rank_score"),0.0) or 0.0,
            "market":_num((fast or {}).get("player_market_score"),0.0) or 0.0,
        })

    chosen=[]

    # First cover entirely missing combinations, favouring more meaningful price
    # bands before micro-priced noise.
    band_priority={"upper":4,"mid":3,"low":2,"micro":1}
    type_priority={"single":2,"lot":1}
    sale_priority={"buy-now":2,"auction":2,"unknown":1}

    while len(chosen)<take:
        eligible=[]
        for row in pool:
            if row["idx"] in selected_set:
                continue
            if player_counts.get(row["player"],0)>=max_per_player:
                continue
            seg=row["segment"]
            novelty=1 if seg not in represented else 0
            eligible.append((
                novelty,
                band_priority.get(seg[0],0),
                sale_priority.get(seg[1],0),
                type_priority.get(seg[2],0),
                row["rank"],
                row["market"],
                -row["idx"],
                row,
            ))
        if not eligible:
            break
        eligible.sort(reverse=True,key=lambda x:x[:7])
        row=eligible[0][7]
        chosen.append(row["idx"])
        selected_set.add(row["idx"])
        represented.add(row["segment"])
        player_counts[row["player"]]=player_counts.get(row["player"],0)+1

    return selected+chosen, chosen


def segment_coverage_summary(candidates, indices, budget):
    counts={}
    for idx in indices or []:
        if not (0 <= int(idx) < len(candidates or [])):
            continue
        item,fast,_att=candidates[int(idx)]
        seg=segment_key(item,fast,budget)
        label="/".join(seg)
        counts[label]=counts.get(label,0)+1
    return {
        "segment_count":len(counts),
        "segments":counts,
        "creates_new_score":False,
        "creates_new_decision":False,
    }
