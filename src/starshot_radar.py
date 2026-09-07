"""Decision-safe Stjärnskott Radar.

Combines attributed player momentum with already scanned listings. It never
creates a buy decision and never infers market reaction without sold evidence.
"""
from __future__ import annotations
from .player_momentum import build_starshot_watchlist


def _listing_player(c):
    return str((c or {}).get("player_name") or "").strip()


def _identity(c):
    return c.get("exact_identity_status") or c.get("identity_status") or "Ej säkert identifierat"


def _total_cost(c):
    for key in ("total_cost", "total_inkopskostnad", "total_purchase_cost"):
        if c.get(key) is not None:
            return c.get(key)
    price=c.get("pris") if c.get("pris") is not None else c.get("price")
    shipping=c.get("frakt") if c.get("frakt") is not None else c.get("shipping")
    if price is None: return None
    try: return float(price)+float(shipping or 0)
    except (TypeError,ValueError): return None


def _sold_evidence(c):
    # Only explicit decision-grade/exact sold evidence may support reaction text.
    comps=c.get("exact_sold_comps") or c.get("verified_exact_sold_comps") or []
    return comps if isinstance(comps,list) else []


def build_starshot_radar(events, candidates):
    watch=build_starshot_watchlist(events)
    by_name={p["player_name"].casefold():p for p in watch.get("players",[])}
    cards={name:[] for name in by_name}
    for c in candidates or []:
        player=_listing_player(c)
        if not player or player.casefold() not in by_name: continue
        cards[player.casefold()].append({
            "title":c.get("titel") or c.get("title") or "Okänt kort",
            "url":c.get("lank") or c.get("url"),
            "price":c.get("pris") if c.get("pris") is not None else c.get("price"),
            "total_cost":_total_cost(c),
            "existing_decision":c.get("decision") or c.get("recommendation") or "Ingen bedömning",
            "identity_status":_identity(c),
            "sellability":c.get("sellability") or c.get("liquidity_label"),
            "exact_sold_comp_count":len(_sold_evidence(c)),
            "decision_changed":False,
        })
    players=[]
    for p in watch.get("players",[]):
        pcards=cards.get(p["player_name"].casefold(),[])
        comp_count=sum(x["exact_sold_comp_count"] for x in pcards)
        players.append({**p,"cards":pcards,"card_count":len(pcards),
            "market_reaction_status":"Marknadsreaktion ej verifierad",
            "market_reaction_reason":("Exact SOLD-data finns på kopplade kort men tidsserie för före/efter momentum är inte verifierad."
                                      if comp_count else "Ingen verifierad Exact SOLD-evidens på kopplade kort."),
            "buy_signal_created":False})
    return {"status":"READY" if players else "INSUFFICIENT_DATA","players":players,
            "player_count":len(players),"matched_card_count":sum(x["card_count"] for x in players),
            "note":"Momentum är upptäcktskontext. Befintligt kortbeslut står kvar; radarn skapar inte KÖP, värdering eller maxbud."}
