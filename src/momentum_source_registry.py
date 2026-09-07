"""Transparent source registry for Player Momentum.

Capabilities describe how a source may contribute. Registry presence never
means that automated ingestion is connected.
"""
SOURCES=[
    {"name":"NHL.com Prospects","source_type":"official_league","sports":["hockey"],
     "supports":["ranking_rise","senior_debut","role_increase","performance_breakout","draft_event"],
     "automated_ingestion":False},
    {"name":"Upper Deck Checklists","source_type":"official_manufacturer","sports":["hockey"],
     "supports":["checklist_or_rookie_release"],"automated_ingestion":False},
    {"name":"Manufacturer / official checklist","source_type":"official_manufacturer","sports":["football","soccer","hockey"],
     "supports":["checklist_or_rookie_release"],"automated_ingestion":False},
    {"name":"Prospect ranking publisher","source_type":"prospect_ranking","sports":["hockey","football","soccer"],
     "supports":["ranking_rise"],"automated_ingestion":False},
]
def source_registry():
    return {"sources":[dict(x) for x in SOURCES],
            "connected_count":sum(1 for x in SOURCES if x["automated_ingestion"]),
            "note":"Källregistret beskriver tillåtna roller; det påstår inte att en integration är live."}
