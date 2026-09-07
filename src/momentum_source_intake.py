"""Source intake for Player Momentum.

Transforms permitted, attributed source observations into the strict event
schema consumed by player_momentum. This module performs no web scraping and
does not infer events from prose.
"""
from __future__ import annotations
from .player_momentum import normalize_momentum_event

SOURCE_KINDS={
    "official_league","official_team","official_manufacturer",
    "prospect_ranking","checklist_publisher","manual_research",
}

def ingest_momentum_records(records, *, batch_source=None):
    accepted=[]; rejected=[]
    for i,raw in enumerate(records or []):
        row=dict(raw or {})
        source_kind=str(row.get("source_type") or batch_source or "").strip()
        if source_kind not in SOURCE_KINDS:
            rejected.append({"index":i,"reason":"unsupported_source_type","record":row})
            continue
        row["source_type"]=source_kind
        event=normalize_momentum_event(row)
        if event.get("status")!="READY":
            rejected.append({"index":i,"reason":event.get("reason") or "invalid_event","record":row})
            continue
        accepted.append(event)
    return {
        "status":"READY" if accepted else "NO_ACCEPTED_EVENTS",
        "accepted":accepted,"rejected":rejected,
        "accepted_count":len(accepted),"rejected_count":len(rejected),
        "automated_scraping_used":False,
        "note":"Intaget accepterar endast strukturerade, attribuerade observationer. Fri text omvandlas inte automatiskt till momentumfakta.",
    }
