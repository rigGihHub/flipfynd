from __future__ import annotations


def _sport_state(coverage: dict | None, refresh_plan: dict | None) -> dict:
    coverage = coverage or {}
    refresh_plan = refresh_plan or {}
    freshness = str(coverage.get("freshness") or "unknown").lower()
    due = bool(refresh_plan.get("due"))
    complete = bool(coverage.get("complete"))

    if due or freshness == "stale":
        state = "needs_update"
        label = "Behöver uppdateras"
    elif not complete:
        state = "building"
        label = "Marknaden byggs upp"
    elif freshness in {"fresh", "aging"}:
        state = "ready"
        label = "Tillräckligt färsk"
    else:
        state = "unknown"
        label = "Status okänd"

    return {
        "state": state,
        "label": label,
        "complete": complete,
        "freshness": freshness,
        "due": due,
        "loaded_page_count": int(coverage.get("loaded_page_count", 0) or 0),
        "next_page": int(coverage.get("next_page", 1) or 1),
        "age_hours": coverage.get("age_hours"),
        "missing_pages": list(coverage.get("missing_pages") or []),
    }


def build_market_overview(
    hockey_coverage: dict | None,
    football_coverage: dict | None,
    hockey_refresh: dict | None,
    football_refresh: dict | None,
) -> dict:
    """Build a user-facing market status without changing fetch/ranking logic."""
    sports = {
        "hockey": _sport_state(hockey_coverage, hockey_refresh),
        "football": _sport_state(football_coverage, football_refresh),
    }
    states = {item["state"] for item in sports.values()}

    if "needs_update" in states:
        status = "needs_update"
        headline = "Marknaden behöver uppdateras"
        message = "Minst en marknad har data som bör läsas om innan du förlitar dig på färskhetskänsliga fynd."
    elif "building" in states:
        status = "building"
        headline = "Marknaden är användbar men inte fullt inläst"
        message = "Du kan söka fynd nu. Full marknadstäckning kan byggas vidare i avancerade inställningar."
    elif states == {"ready"}:
        status = "ready"
        headline = "Marknaden är tillräckligt färsk"
        message = "Du kan söka fynd direkt. En vanlig uppdatering räcker normalt för att fånga nya annonser."
    else:
        status = "unknown"
        headline = "Marknadsstatus behöver kontrolleras"
        message = "Data finns inläst, men FlipFynd kan inte säkert bedöma färskheten just nu."

    return {
        "status": status,
        "headline": headline,
        "message": message,
        "sports": sports,
        "all_complete": all(item["complete"] for item in sports.values()),
        "any_refresh_due": any(item["due"] for item in sports.values()),
    }
