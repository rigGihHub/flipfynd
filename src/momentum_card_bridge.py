"""Bridge momentum players to already scanned listings without changing decisions."""
from __future__ import annotations

def bridge_momentum_to_cards(watchlist, candidates):
    names={str(x.get("player_name") or "").strip().casefold():x for x in (watchlist or {}).get("players",[]) if x.get("player_name")}
    matches=[]
    for c in candidates or []:
        player=str(c.get("player_name") or "").strip()
        if not player or player.casefold() not in names: continue
        m=names[player.casefold()]
        matches.append({
            "player_name":player,"title":c.get("titel") or "Okänt kort",
            "url":c.get("lank"),"existing_decision":c.get("decision") or c.get("recommendation"),
            "momentum_event_count":m.get("event_count"),"momentum_source_count":m.get("source_count"),
            "decision_changed":False,"valuation_changed":False,"max_bid_changed":False,
        })
    return {"status":"READY" if matches else "NO_MATCHES","matches":matches,
            "note":"Bryggan visar bara att en redan skannad listing gäller en spelare med dokumenterade momentumhändelser. Den ändrar inga köpbeslut."}
