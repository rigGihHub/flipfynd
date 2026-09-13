"""Safe query broadening for comp research.

The ladder improves recall when marketplace titles differ in set naming or season
format. It only creates search queries/links. It never classifies results as exact
SOLD and never affects valuation or BUY decisions.
"""
from __future__ import annotations

import re
from urllib.parse import quote_plus

from src.exact_comp_hunter import build_exact_query


def _clean(v) -> str:
    return " ".join(str(v or "").strip().split())


def _season_variants(season: str) -> list[str]:
    s = _clean(season)
    if not s:
        return []
    out = [s]
    m = re.fullmatch(r"((?:19|20)\d{2})[-/](\d{2})", s)
    if m:
        y1, y2 = m.groups()
        out.extend([f"{y1}-{y2}", f"{y1}/{y2}"])
    m2 = re.fullmatch(r"((?:19|20)\d{2})[-/]((?:19|20)\d{2})", s)
    if m2:
        y1, y2 = m2.groups()
        out.extend([f"{y1}-{y2[-2:]}", f"{y1}/{y2[-2:]}"])
    seen=[]
    for x in out:
        if x and x not in seen:
            seen.append(x)
    return seen


def _q(parts: list[str]) -> str:
    seen=set(); out=[]
    for p in parts:
        p=_clean(p)
        key=p.casefold()
        if p and key not in seen:
            seen.add(key); out.append(p)
    return " ".join(out)


def build_research_query_ladder(identity: dict | None) -> dict:
    """Return strict-to-broad search queries from structured research identity.

    Broadening is intentionally limited: player and card number are retained on
    every useful rung. The function only aids discovery; downstream verification
    must still prove exact identity and sold status.
    """
    d = identity or {}
    player = _clean(d.get("player_name"))
    set_name = _clean(d.get("set_name"))
    season = _clean(d.get("season"))
    number = _clean(d.get("card_number"))
    parallel = _clean(d.get("parallel"))

    if not player or not number:
        return {"ready": False, "queries": [], "reason": "spelare och kortnummer krävs"}

    num = number if number.startswith("#") else f"#{number}"
    rows=[]

    def add(level: str, label: str, parts: list[str], note: str):
        query=_q(parts)
        if not query or any(r["query"].casefold()==query.casefold() for r in rows):
            return
        enc=quote_plus(query)
        rows.append({
            "level": level,
            "label": label,
            "query": query,
            "note": note,
            "ebay_sold_url": f"https://www.ebay.com/sch/i.html?_nkw={enc}&LH_Sold=1&LH_Complete=1",
            "tradera_url": f"https://www.tradera.com/search?q={enc}",
            "sportscardspro_url": f"https://www.sportscardspro.com/search-products?exclude-variants=false&q={enc}&region-name=all&type=prices&view=grid",
        })

    strict = build_exact_query(d)
    if strict:
        add("STRICT", "Exakt strukturerad sökning", [strict], "Börja här. Minst risk för fel variant.")

    seasons = _season_variants(season) or ([season] if season else [])
    for sv in seasons[:2]:
        add("FORMAT", "Alternativ säsongsform", [player, sv, set_name, num, parallel], "Samma identitet, annan vanlig säsongsnotation.")

    if set_name:
        add("NO_SET", "Utan setnamn", [player, season, num, parallel], "Fångar annonser där set/program skrivits annorlunda. Kräver extra manuell kontroll.")
    if parallel:
        add("NO_PARALLEL", "Utan parallel", [player, season, set_name, num], "Fångar otydligt namngivna varianter. Resultat får inte antas vara samma parallel.")

    # Minimal discovery rung retains the two strongest anchors plus season when known.
    add("MINIMAL", "Minimal kandidatjakt", [player, season, num], "Endast kandidatjakt. Varje träff måste verifieras mot set och variant innan SOLD kan räknas.")

    return {
        "ready": True,
        "queries": rows[:5],
        "query_count": min(5, len(rows)),
        "note": "Query ladder breddar bara research. Ingen träff blir exact SOLD, värdering eller KÖP utan ordinarie verifiering.",
    }
