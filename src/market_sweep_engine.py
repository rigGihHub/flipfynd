"""Market Sweep Engine.

Systematically gives omitted, already-fetched category listings a chance at the
existing full analysis through distinct market lenses. It creates no card facts,
valuation, score, max price or decision.
"""
from __future__ import annotations
from statistics import median

from src.bad_listing_hunter import build_bad_listing_signal
from src.lot_treasure_hunter import build_lot_treasure_signal


def _n(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _quartiles(values):
    vals=sorted(float(v) for v in values if v is not None)
    if not vals:
        return None, None
    n=len(vals)
    q1=vals[max(0, min(n-1, int((n-1)*0.25)))]
    q3=vals[max(0, min(n-1, int((n-1)*0.75)))]
    return q1, q3


def market_sweep_tags(item, fast, attention, *, low_price_cutoff=None):
    item, fast, attention = item or {}, fast or {}, attention or {}
    tags=[]

    price=_n(item.get("pris"), -1)
    if price >= 0 and low_price_cutoff is not None and price <= low_price_cutoff:
        tags.append("cheap-quarter")

    # Tradera category fetch starts at newest listings; low page numbers are
    # therefore a freshness lens, not a claim about exact listing time.
    page=item.get("sida")
    try:
        page=int(page)
    except (TypeError, ValueError):
        page=None
    if page is not None and page <= 2:
        tags.append("newest-pages")

    if fast.get("is_ending_soon_candidate") or fast.get("ending_soon_candidate"):
        tags.append("ending-soon")

    if build_bad_listing_signal(fast).get("candidate"):
        tags.append("bad-listing")

    if fast.get("is_lot") or fast.get("lot_count"):
        tags.append("lot")
        if build_lot_treasure_signal(fast).get("candidate"):
            tags.append("lot-treasure")

    if fast.get("rookie_importance_matched") or fast.get("mispriced_rookie_candidate"):
        tags.append("rookie-prospect")

    if (
        _n(fast.get("variant_hierarchy_variant_rung")) > 0
        or bool(fast.get("valuable_card_tags"))
        or _n(fast.get("valuable_card_structure_score")) > 0
    ):
        tags.append("variant-structure")

    if item.get("source_type") == "tradera_api_search_expansion":
        tags.append("search-expansion")

    if _n((attention or {}).get("score")) > 0:
        tags.append("market-attention")

    return list(dict.fromkeys(tags))


def build_market_sweep_map(candidates):
    candidates=candidates or []
    prices=[_n((item or {}).get("pris"), -1) for item,_fast,_attention in candidates]
    prices=[p for p in prices if p >= 0]
    q1,_q3=_quartiles(prices)

    rows=[]; counts={}
    for idx,(item,fast,attention) in enumerate(candidates):
        tags=market_sweep_tags(item,fast,attention,low_price_cutoff=q1)
        for tag in tags:
            counts[tag]=counts.get(tag,0)+1
        rows.append({
            "index":idx,
            "tags":tags,
            "player_name":(fast or {}).get("player_name"),
            "rank_score":_n((fast or {}).get("rank_score")),
        })
    return {
        "rows":rows,
        "route_counts":counts,
        "candidate_count":len(candidates),
        "low_price_cutoff":q1,
        "creates_new_score":False,
        "creates_new_decision":False,
        "creates_new_value":False,
    }


def select_market_sweep_indices(
    candidates,
    already_selected,
    *,
    extra_limit=8,
    total_hard_cap=45,
    max_per_player=2,
):
    """Choose omitted candidates to broaden market-segment coverage."""
    sweep=build_market_sweep_map(candidates)
    selected={int(i) for i in (already_selected or []) if 0 <= int(i) < len(candidates or [])}
    room=max(0,int(total_hard_cap)-len(selected))
    take=min(max(0,int(extra_limit)),room)
    if take <= 0:
        return []

    covered=set()
    player_counts={}
    for row in sweep["rows"]:
        if row["index"] in selected:
            covered.update(row["tags"])
            key=str(row.get("player_name") or f"__unknown_{row['index']}").casefold()
            player_counts[key]=player_counts.get(key,0)+1

    pool=[r for r in sweep["rows"] if r["index"] not in selected and r["tags"]]
    chosen=[]
    while pool and len(chosen)<take:
        eligible=[]
        for row in pool:
            key=str(row.get("player_name") or f"__unknown_{row['index']}").casefold()
            if player_counts.get(key,0)>=max_per_player:
                continue
            novelty=len(set(row["tags"])-covered)
            # Existing fast rank is only a tie-breaker. No new opportunity score.
            eligible.append((novelty,len(row["tags"]),row["rank_score"],-row["index"],row))
        if not eligible:
            break
        eligible.sort(reverse=True,key=lambda x:x[:4])
        row=eligible[0][4]
        chosen.append(row["index"])
        covered.update(row["tags"])
        key=str(row.get("player_name") or f"__unknown_{row['index']}").casefold()
        player_counts[key]=player_counts.get(key,0)+1
        pool=[r for r in pool if r["index"]!=row["index"]]
    return chosen
