"""Interpret lookup failures without confusing missing prices with no bargains."""

def price_research_problem(debug):
    debug = debug or {}
    statuses = debug.get("price_research_status_counts") or {}
    limited = debug.get("inventory_price_stop") == "API_LIMIT" or any(
        "HTTP_429" in key for key, count in statuses.items() if count)
    failed = any(key.startswith("COMPARISON_") for key, count in statuses.items() if count)
    incomplete = bool(debug.get("inventory_price_remaining"))
    if limited:
        return "eBay har stoppat prisanropen (API-gräns). Prisundersökningen är ofullständig; detta betyder inte att fynd saknas. Tidigare sparade resultat finns kvar via deras söklänk."
    if failed or incomplete:
        return "Prisundersökningen är ofullständig. Vissa kort saknar priskontroll; resultatet kan därför inte avgöra om fler fynd finns."
    return None
