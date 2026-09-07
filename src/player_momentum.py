"""Evidence-first player momentum layer.

This layer surfaces *changes* around players. It is discovery context only:
it never upgrades a listing to KÖP, never changes valuation/max bid, and never
treats prospect reputation as a sold comp.
"""
from __future__ import annotations
from datetime import datetime, timezone

EVENT_TYPES={
    "ranking_rise","senior_debut","role_increase","performance_breakout",
    "national_team_callup","draft_event","transfer_or_contract",
    "checklist_or_rookie_release","card_market_velocity_change",
}

def _parse_dt(v):
    if not v: return None
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None

def normalize_momentum_event(event, *, now=None):
    e=dict(event or {})
    player=str(e.get("player_name") or "").strip()
    kind=str(e.get("event_type") or "").strip()
    source=str(e.get("source_name") or "").strip()
    source_url=str(e.get("source_url") or "").strip()
    occurred=_parse_dt(e.get("occurred_at"))
    observed=_parse_dt(e.get("observed_at"))
    if not player or kind not in EVENT_TYPES or not source or not source_url or not occurred:
        return {"status":"REJECTED","reason":"missing_or_invalid_evidence"}
    return {
        "status":"READY","player_name":player,"sport":e.get("sport"),
        "event_type":kind,"occurred_at":occurred.isoformat(),
        "observed_at":observed.isoformat() if observed else None,
        "source_name":source,"source_url":source_url,
        "source_type":e.get("source_type") or "external_research",
        "detail":e.get("detail"),
        "ranking_before":e.get("ranking_before"),
        "ranking_after":e.get("ranking_after"),
        "metric_before":e.get("metric_before"),
        "metric_after":e.get("metric_after"),
    }

def build_player_momentum(events, *, player_name=None):
    valid=[]
    for e in events or []:
        n=normalize_momentum_event(e)
        if n.get("status")=="READY":
            if player_name and n["player_name"].casefold()!=str(player_name).casefold():
                continue
            valid.append(n)
    if not valid:
        return {"status":"INSUFFICIENT_DATA","available":False,"events":[]}

    valid.sort(key=lambda x:(x["occurred_at"],x["source_name"]),reverse=True)
    types=sorted({x["event_type"] for x in valid})
    sources=sorted({x["source_name"] for x in valid})
    players=sorted({x["player_name"] for x in valid})
    return {
        "status":"READY","available":True,"events":valid,
        "event_count":len(valid),"event_types":types,"source_count":len(sources),
        "players":players,
        "momentum_score":None,"buy_signal_created":False,
        "valuation_changed":False,"max_bid_changed":False,
        "note":"Momentum är evidensbaserad upptäcktskontext. Ingen prospect-/nyhetssignal får ensam skapa KÖP, värdering eller maxbud.",
    }

def build_starshot_watchlist(events):
    grouped={}
    for e in events or []:
        n=normalize_momentum_event(e)
        if n.get("status")!="READY": continue
        grouped.setdefault(n["player_name"],[]).append(n)
    rows=[]
    for player, evs in grouped.items():
        summary=build_player_momentum(evs,player_name=player)
        rows.append({
            "player_name":player,
            "sport":next((x.get("sport") for x in evs if x.get("sport")),None),
            "event_count":summary["event_count"],
            "event_type_count":len(summary["event_types"]),
            "source_count":summary["source_count"],
            "latest_event_at":summary["events"][0]["occurred_at"],
            "events":summary["events"],
            "buy_signal_created":False,
        })
    # factual ordering only: newest observed change, then breadth, then name.
    rows.sort(key=lambda x:(x["latest_event_at"],x["event_type_count"],x["source_count"],x["player_name"]),reverse=True)
    return {
        "status":"READY" if rows else "INSUFFICIENT_DATA",
        "available":bool(rows),"players":rows,
        "ranking_basis":"latest evidence change, then event/source breadth; not a talent forecast",
        "prospect_score_created":False,"buy_signal_created":False,
    }
