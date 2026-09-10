"""Market Gap Hunter 2.0.

Detects thin *active-listing supply* relative to existing FlipFynd demand evidence.
Research-only unless the normal sold/valuation/identity pipeline independently
supports a purchase. No market value, max price or BUY is created here.
"""
from __future__ import annotations
from collections import defaultdict


def _n(v, default=0.0):
    try: return float(v)
    except (TypeError, ValueError): return float(default)


def _player(item):
    return str((item or {}).get("player_name") or "").strip()


def build_market_gap_map(items):
    """Group analyzed active candidates by structured player name."""
    groups=defaultdict(list)
    for item in items or []:
        if not isinstance(item,dict): continue
        player=_player(item)
        if player:
            groups[player.casefold()].append(item)

    rows=[]
    for key, group in groups.items():
        sample=group[0]
        player=_player(sample)
        supply=len(group)
        demand=max((_n(i.get("player_card_demand_score")) for i in group), default=0.0)
        demand_verified=any(
            bool(i.get("player_card_demand_verified"))
            or bool(i.get("player_card_demand_evidence_count"))
            for i in group
        )
        sold=max((int(_n(i.get("sold_comparable_count"))) for i in group), default=0)
        safe_value=any(i.get("valuation_display_safe") is True for i in group)

        # "Thin" is deliberately descriptive and pool-relative: 1-2 active
        # candidates for this structured player in the current analyzed pool.
        thin_supply=supply <= 2
        demand_signal=demand > 0
        candidate=thin_supply and demand_signal
        if not candidate:
            status="NO_GAP_SIGNAL"
        elif sold >= 2 and safe_value:
            status="GAP_WITH_MARKET_EVIDENCE"
        else:
            status="GAP_RESEARCH_ONLY"

        blockers=[]
        if candidate and sold < 2:
            blockers.append("Färre än 2 matchande verifierade försäljningar.")
        if candidate and not safe_value:
            blockers.append("Marknadsvärde är inte godkänt för säker visning.")
        if candidate and not demand_verified:
            blockers.append("Efterfrågesignalen saknar uttryckligt verifieringsstöd.")

        rows.append({
            "player_name":player,
            "active_candidate_supply":supply,
            "player_card_demand_score":demand,
            "demand_verified":demand_verified,
            "sold_comparable_count":sold,
            "valuation_display_safe":safe_value,
            "thin_supply":thin_supply,
            "candidate":candidate,
            "status":status,
            "blockers":blockers,
            "can_create_buy_decision":False,
            "can_create_market_value":False,
            "can_create_max_price":False,
        })

    rows.sort(key=lambda r:(
        r["status"]=="GAP_WITH_MARKET_EVIDENCE",
        r["candidate"],
        r["player_card_demand_score"],
        -r["active_candidate_supply"],
    ), reverse=True)
    return {
        "rows":rows,
        "candidate_count":sum(1 for r in rows if r["candidate"]),
        "creates_new_score":False,
        "creates_new_decision":False,
        "creates_new_value":False,
        "note":"Tunt utbud gäller endast den aktuella analyserade kandidatpoolen, inte hela marknaden.",
    }


def build_market_gap_queue(items, limit=8):
    report=build_market_gap_map(items)
    rows=[r for r in report["rows"] if r["candidate"]]
    return {
        "rows":rows[:max(0,int(limit))],
        "candidate_count":report["candidate_count"],
        "creates_new_decision":False,
        "creates_new_value":False,
    }
