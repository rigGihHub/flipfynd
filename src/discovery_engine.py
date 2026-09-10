"""Discovery Engine 2.0: broaden candidate *analysis* without weakening BUY rules.

The engine uses only signals already produced by FlipFynd's fast analysis.
It creates no card facts, valuation, max price, decision, or synthetic
"opportunity score". Its only job is to ensure different discovery hypotheses
receive a chance at the existing full analysis.
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


def _hunter_tags(item, fast, attention, *, price_median=None, demand_median=0.0):
    item, fast, attention = item or {}, fast or {}, attention or {}
    tags = []

    if fast.get("is_hidden_find_candidate"):
        tags.append("hidden-find")
    if fast.get("misclassified_card_candidate") or fast.get("is_information_edge_candidate"):
        tags.append("bad-listing")
    if build_bad_listing_signal(fast).get("candidate") and "bad-listing" not in tags:
        tags.append("bad-listing")
    if fast.get("rookie_importance_matched") or fast.get("mispriced_rookie_candidate"):
        tags.append("rookie-prospect")
    if (
        _n(fast.get("variant_hierarchy_variant_rung")) > 0
        or _n(fast.get("valuable_card_structure_score")) > 0
        or bool(fast.get("valuable_card_tags"))
    ):
        tags.append("variant-scarcity")

    price = _n(item.get("pris"), -1)
    demand = _n(fast.get("player_card_demand_score"))
    if price >= 0 and price_median is not None and price <= price_median:
        tags.append("low-price")
        if demand > 0 and demand >= demand_median:
            tags.append("low-price-demand")

    if fast.get("is_ending_soon_candidate") or fast.get("ending_soon_candidate"):
        tags.append("ending-soon")
    if fast.get("is_buy_now_candidate") or fast.get("buy_now_candidate"):
        tags.append("buy-now")
    if fast.get("is_lot") or fast.get("lot_count"):
        tags.append("lot-research")
        if build_lot_treasure_signal(fast).get("candidate"):
            tags.append("lot-treasure")
    if _n(attention.get("score")) > 0:
        tags.append("market-attention")
    return tags


def build_discovery_map(candidates):
    """Describe discovery coverage using existing signals only."""
    candidates = candidates or []
    prices = [_n((item or {}).get("pris"), -1) for item, _fast, _att in candidates]
    prices = [p for p in prices if p >= 0]
    price_median = median(prices) if prices else None
    demands = [_n((fast or {}).get("player_card_demand_score")) for _item, fast, _att in candidates]
    positive = [d for d in demands if d > 0]
    demand_median = median(positive) if positive else 0.0

    rows, counts = [], {}
    for idx, (item, fast, attention) in enumerate(candidates):
        tags = _hunter_tags(
            item, fast, attention,
            price_median=price_median,
            demand_median=demand_median,
        )
        for tag in tags:
            counts[tag] = counts.get(tag, 0) + 1
        rows.append({
            "index": idx,
            "tags": tags,
            "rank_score": _n((fast or {}).get("rank_score")),
            "player_name": (fast or {}).get("player_name"),
        })
    return {
        "rows": rows,
        "hunter_counts": counts,
        "candidate_count": len(candidates),
        "creates_new_decision": False,
        "creates_new_score": False,
    }


def select_discovery_indices(
    candidates,
    already_selected,
    *,
    extra_limit=10,
    total_hard_cap=45,
    max_per_player=2,
):
    """Pick omitted candidates that add distinct discovery hypotheses.

    Existing selected candidates are never removed. Selection prefers a new
    hunter profile and player diversity, then the existing fast rank_score.
    """
    discovery = build_discovery_map(candidates)
    selected = {int(i) for i in (already_selected or []) if 0 <= int(i) < len(candidates or [])}
    room = max(0, int(total_hard_cap) - len(selected))
    take = min(max(0, int(extra_limit)), room)
    if take <= 0:
        return []

    covered = set()
    player_counts = {}
    for row in discovery["rows"]:
        if row["index"] in selected:
            covered.update(row["tags"])
            key = str(row.get("player_name") or f"__unknown_{row['index']}").casefold()
            player_counts[key] = player_counts.get(key, 0) + 1

    pool = [r for r in discovery["rows"] if r["index"] not in selected and r["tags"]]
    chosen = []
    while pool and len(chosen) < take:
        eligible = []
        for row in pool:
            key = str(row.get("player_name") or f"__unknown_{row['index']}").casefold()
            if player_counts.get(key, 0) >= max_per_player:
                continue
            novelty = len(set(row["tags"]) - covered)
            eligible.append((novelty, len(row["tags"]), row["rank_score"], -row["index"], row))
        if not eligible:
            break
        eligible.sort(reverse=True, key=lambda x: x[:4])
        row = eligible[0][4]
        chosen.append(row["index"])
        covered.update(row["tags"])
        key = str(row.get("player_name") or f"__unknown_{row['index']}").casefold()
        player_counts[key] = player_counts.get(key, 0) + 1
        pool = [r for r in pool if r["index"] != row["index"]]

    return chosen
