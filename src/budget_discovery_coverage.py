"""Budget-aware discovery coverage.

Ensures full analysis is not dominated by ultra-cheap listings when the user's
budget allows materially different price bands. This changes only WHICH already
filtered candidates receive full analysis; it does not alter valuation, score,
max price, risk, or BUY rules.
"""
from __future__ import annotations


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _band(price, budget):
    if price is None or budget is None or budget <= 0:
        return "unknown"
    ratio = price / budget
    if ratio <= 0.05:
        return "micro"
    if ratio <= 0.20:
        return "low"
    if ratio <= 0.50:
        return "mid"
    return "upper"


def add_budget_coverage_indices(candidates, selected_indices, *, budget, extra_slots=8, hard_cap=38, max_per_player=2):
    """Add omitted candidates from underrepresented price bands.

    Existing candidate ranking is used only inside each band. No new deal score
    is invented. At least one candidate can be added from each represented band.
    """
    selected = list(dict.fromkeys(int(i) for i in (selected_indices or []) if 0 <= int(i) < len(candidates or [])))
    selected_set=set(selected)
    room=max(0, int(hard_cap)-len(selected))
    take=min(max(0,int(extra_slots)),room)
    if take<=0:
        return selected, []

    band_rows={"micro":[],"low":[],"mid":[],"upper":[]}
    player_counts={}
    for idx in selected:
        item, fast, _att = candidates[idx]
        player=str((fast or {}).get("player_name") or f"__unknown_{idx}").casefold()
        player_counts[player]=player_counts.get(player,0)+1

    for idx,(item,fast,_att) in enumerate(candidates or []):
        if idx in selected_set:
            continue
        price=_num((item or {}).get("pris"))
        band=_band(price,_num(budget))
        if band=="unknown":
            continue
        player=str((fast or {}).get("player_name") or f"__unknown_{idx}").casefold()
        band_rows[band].append((
            _num((fast or {}).get("rank_score"),0.0) or 0.0,
            _num((fast or {}).get("player_market_score"),0.0) or 0.0,
            -idx,
            idx,
            player,
        ))

    for rows in band_rows.values():
        rows.sort(reverse=True)

    represented={
        _band(_num((candidates[i][0] or {}).get("pris")),_num(budget))
        for i in selected
    }
    chosen=[]

    # First, cover missing price bands so a 1 000 kr budget is not represented
    # only by 5–20 kr cards.
    for band in ("upper","mid","low","micro"):
        if len(chosen)>=take:
            break
        if band in represented or not band_rows[band]:
            continue
        for _rank,_market,_neg,idx,player in band_rows[band]:
            if player_counts.get(player,0)>=max_per_player:
                continue
            chosen.append(idx)
            selected_set.add(idx)
            player_counts[player]=player_counts.get(player,0)+1
            represented.add(band)
            break

    # Fill remaining slots round-robin across bands, still respecting player diversity.
    while len(chosen)<take:
        added=False
        for band in ("upper","mid","low","micro"):
            while band_rows[band]:
                _rank,_market,_neg,idx,player=band_rows[band].pop(0)
                if idx in selected_set or player_counts.get(player,0)>=max_per_player:
                    continue
                chosen.append(idx)
                selected_set.add(idx)
                player_counts[player]=player_counts.get(player,0)+1
                added=True
                break
            if len(chosen)>=take:
                break
        if not added:
            break

    return selected + chosen, chosen


def budget_coverage_summary(candidates, indices, budget):
    counts={"micro":0,"low":0,"mid":0,"upper":0,"unknown":0}
    for idx in indices or []:
        if 0 <= int(idx) < len(candidates or []):
            item=candidates[int(idx)][0]
            counts[_band(_num((item or {}).get("pris")),_num(budget))]+=1
    return counts
