"""Market Coverage Autopilot.

Chooses the next safe read-only market fetch action from existing coverage and
freshness state. It does not fetch by itself; the UI starts the existing fetcher
with the selected mode. No ranking, valuation or BUY logic is changed.
"""
from __future__ import annotations


def _sport_need(name, coverage, refresh):
    coverage=coverage or {}
    refresh=refresh or {}
    return {
        "name":name,
        "complete":bool(coverage.get("complete")),
        "loaded_pages":int(coverage.get("loaded_page_count",0) or 0),
        "next_page":int(coverage.get("next_page",1) or 1),
        "freshness":str(coverage.get("freshness") or "unknown").lower(),
        "refresh_due":bool(refresh.get("due")),
        "missing_pages":list(coverage.get("missing_pages") or []),
    }


def build_autopilot_plan(hockey_coverage, football_coverage, hockey_refresh, football_refresh):
    sports=[
        _sport_need("Hockey - NHL",hockey_coverage,hockey_refresh),
        _sport_need("Fotboll",football_coverage,football_refresh),
    ]

    stale=[s for s in sports if s["refresh_due"] or s["freshness"]=="stale"]
    building=[s for s in sports if not s["complete"]]

    if stale:
        # Freshness wins before deeper coverage. Both sports can be refreshed in
        # one existing all-category incremental run, avoiding extra clicks.
        return {
            "status":"REFRESH",
            "category":"__all__",
            "mode":"incremental",
            "label":"Uppdatera och förbättra marknaden",
            "reason":"Minst en marknad behöver färskare annonser. FlipFynd uppdaterar båda i samma körning.",
            "sports":sports,
            "creates_decision":False,
        }

    if building:
        # A single all-category market batch continues both incomplete markets.
        return {
            "status":"BUILD",
            "category":"__all__",
            "mode":"market_batch",
            "label":"Bygg ut marknaden automatiskt",
            "reason":"Marknaden är färsk nog men inte fullt inläst. FlipFynd fortsätter bakåt för båda sporterna i samma körning.",
            "sports":sports,
            "creates_decision":False,
        }

    return {
        "status":"READY",
        "category":None,
        "mode":None,
        "label":"Marknaden är redo",
        "reason":"Båda sporterna är tillräckligt färska och fullständigt inlästa enligt nuvarande täckningsstatus.",
        "sports":sports,
        "creates_decision":False,
    }


def autopilot_progress_text(plan):
    plan=plan or {}
    if plan.get("status")=="BUILD":
        incomplete=[s for s in plan.get("sports",[]) if not s.get("complete")]
        if not incomplete:
            return "Ingen marknad behöver byggas ut."
        parts=[f"{s['name']}: {s['loaded_pages']} sidor, nästa {s['next_page']}" for s in incomplete]
        return " · ".join(parts)
    if plan.get("status")=="REFRESH":
        return "Färskhet prioriteras före djupare marknadstäckning."
    return "Ingen åtgärd behövs."
