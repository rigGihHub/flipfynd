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



def _result_sport(item):
    text = str(
        (item or {}).get("source_category")
        or (item or {}).get("sport")
        or ""
    ).casefold()
    if "hockey" in text or "nhl" in text:
        return "Hockey - NHL"
    if "fotboll" in text or "football" in text or "soccer" in text:
        return "Fotboll"
    return None


def _quality_stats(results):
    stats = {
        "Hockey - NHL": {"analyzed": 0, "verified": 0, "promising": 0, "safe_value": 0},
        "Fotboll": {"analyzed": 0, "verified": 0, "promising": 0, "safe_value": 0},
    }
    for item in results or []:
        if not isinstance(item, dict):
            continue
        sport = _result_sport(item)
        if sport not in stats:
            continue
        row = stats[sport]
        row["analyzed"] += 1

        try:
            certainty = float(
                item.get("ranking_confidence_score")
                if item.get("ranking_confidence_score") is not None
                else item.get("deal_confidence_score")
                if item.get("deal_confidence_score") is not None
                else item.get("confidence")
                or 0
            )
        except (TypeError, ValueError):
            certainty = 0.0

        try:
            potential = float(item.get("deal_score") or 0)
        except (TypeError, ValueError):
            potential = 0.0

        sold = int(item.get("sold_comparable_count") or 0)
        identity_ok = bool(
            item.get("exact_identity_gate_supports_exact_comp_search")
            or item.get("exact_identity_gate_status") in {"READY", "EXACT", "STRONG"}
        )
        safe_value = item.get("valuation_display_safe") is True
        decision = str(
            item.get("beslut")
            or item.get("decision")
            or item.get("recommendation")
            or ""
        ).upper()

        if safe_value:
            row["safe_value"] += 1
        if potential >= 55:
            row["promising"] += 1
        if (
            (decision.startswith("KÖP") or decision.startswith("KOP"))
            and certainty >= 60
            and sold >= 2
            and identity_ok
            and safe_value
        ):
            row["verified"] += 1
    return stats


def _coverage_need_score(sport, quality):
    """Prioritise a weakly covered market without inventing a deal score."""
    score = 0
    reasons = []

    if not sport["complete"]:
        score += 4
        reasons.append("marknaden är inte fullt inläst")

    if sport["missing_pages"]:
        score += 1
        reasons.append("sidtäckningen har luckor")

    q = quality.get(sport["name"], {})
    analyzed = int(q.get("analyzed", 0) or 0)
    verified = int(q.get("verified", 0) or 0)
    promising = int(q.get("promising", 0) or 0)
    safe_value = int(q.get("safe_value", 0) or 0)

    if analyzed == 0:
        score += 3
        reasons.append("inga analyserade kandidater finns ännu")
    elif analyzed < 8:
        score += 2
        reasons.append("få kandidater har analyserats")

    if verified == 0:
        score += 3
        reasons.append("inga verifierade fynd finns i senaste analysen")
    if promising == 0:
        score += 2
        reasons.append("inga lovande kandidater finns i senaste analysen")
    if safe_value == 0:
        score += 1
        reasons.append("inga kandidater har säkert visningsbart marknadsvärde")

    # When evidence need is tied, fewer loaded pages should be built first.
    score += max(0.0, 1.0 - min(1.0, sport["loaded_pages"] / 24.0))

    return score, reasons

def build_autopilot_plan(hockey_coverage, football_coverage, hockey_refresh, football_refresh, analyzed_results=None):
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
        quality = _quality_stats(analyzed_results)
        scored = []
        for sport in building:
            need_score, reasons = _coverage_need_score(sport, quality)
            scored.append((need_score, -sport["loaded_pages"], sport["name"], sport, reasons))
        scored.sort(reverse=True)
        _score, _neg_pages, _name, target, reasons = scored[0]
        q = quality.get(target["name"], {})

        return {
            "status":"BUILD",
            "category":target["name"],
            "mode":"market_batch",
            "label":"Bygg där fyndunderlaget är svagast",
            "reason":(
                f"FlipFynd prioriterar {target['name']} just nu: "
                + (", ".join(reasons[:3]) if reasons else "lägst marknadstäckning")
                + "."
            ),
            "target_sport":target["name"],
            "quality_stats":q,
            "quality_all":quality,
            "need_reasons":reasons,
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
        target=plan.get("target_sport")
        if target:
            chosen=next((s for s in incomplete if s.get("name")==target), None)
            if chosen:
                q=(plan.get("quality_stats") or {})
                return (
                    f"Prioritet: {target} · {chosen['loaded_pages']} sidor inlästa · nästa sida {chosen['next_page']} · "
                    f"{int(q.get('verified',0) or 0)} verifierade fynd · {int(q.get('promising',0) or 0)} lovande kandidater."
                )
        parts=[f"{s['name']}: {s['loaded_pages']} sidor, nästa {s['next_page']}" for s in incomplete]
        return " · ".join(parts)
    if plan.get("status")=="REFRESH":
        return "Färskhet prioriteras före djupare marknadstäckning."
    return "Ingen åtgärd behövs."
