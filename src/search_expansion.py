"""Search Expansion Engine.

Builds conservative Tradera search plans from already structured FlipFynd evidence.
It never invents a player, set, variant, rookie status or card value. Search variants
are discovery queries only; a hit must pass the normal identity/valuation pipeline.
"""
from __future__ import annotations
import os
import re
import unicodedata


CATEGORY_IDS = {
    "Hockey - NHL": 293316,
    "Fotboll": 293311,
}

OFFICIAL_ORDERINGS = (
    "Relevance",
    "PriceAscending",
    "EndDateAscending",
)


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _ascii(value):
    text = unicodedata.normalize("NFKD", _clean(value))
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def build_query_variants(item: dict | None, *, max_queries=6) -> list[dict]:
    """Create broad-to-narrow discovery queries from explicit structured fields only."""
    item = item or {}
    player = _clean(item.get("player_name"))
    if not player:
        return []

    set_name = _clean(item.get("set_name") or item.get("card_set"))
    season = _clean(item.get("season") or item.get("year"))
    queries = []

    def add(query, kind, why):
        q=_clean(query)
        if not q:
            return
        key=q.casefold()
        if any(row["query"].casefold()==key for row in queries):
            return
        queries.append({"query":q,"kind":kind,"why":why})

    add(player, "player-exact", "Exakt strukturerat spelarnamn.")

    ascii_player=_ascii(player)
    if ascii_player.casefold()!=player.casefold():
        add(ascii_player, "diacritic-variant", "Samma spelarnamn utan diakritiska tecken; discovery only.")

    parts=player.split()
    if len(parts)>=2 and len(parts[-1])>=4:
        add(parts[-1], "surname-broad", "Efternamnssökning kan hitta kort där förnamnet saknas.")

    if set_name:
        add(f"{player} {set_name}", "player-set", "Spelare + redan identifierat set/program.")
    if set_name and season:
        add(f"{player} {set_name} {season}", "player-set-season", "Spelare + set + redan identifierad säsong/år.")

    if item.get("rookie_importance_matched") or item.get("mispriced_rookie_candidate"):
        add(f"{player} rookie", "rookie-existing-signal", "Rookie-term används bara eftersom befintlig rookie-signal finns.")

    return queries[:max(0,int(max_queries))]


def build_search_matrix(item: dict | None, category_name: str, *, max_queries=5) -> list[dict]:
    """Expand safe query variants across official Tradera search orderings."""
    category_id=CATEGORY_IDS.get(category_name)
    if not category_id:
        return []
    matrix=[]
    for row in build_query_variants(item,max_queries=max_queries):
        for order_by in OFFICIAL_ORDERINGS:
            matrix.append({
                **row,
                "category_name":category_name,
                "category_id":category_id,
                "order_by":order_by,
                "page_number":1,
                "evidence_only":True,
            })
    return matrix


def build_search_expansion_plan(items, category_name, *, player_limit=6, max_searches=36):
    """Make a deduplicated search plan from strongest existing player evidence."""
    candidates=[]
    seen_players=set()
    sorted_items=sorted(
        [dict(i) for i in (items or []) if isinstance(i,dict)],
        key=lambda i:(
            float(i.get("player_market_score") or 0),
            float(i.get("opportunity_priority_score") or 0),
            float(i.get("rank_score") or 0),
        ),
        reverse=True,
    )
    for item in sorted_items:
        player=_clean(item.get("player_name"))
        if not player or player.casefold() in seen_players:
            continue
        # Do not expand low-confidence player text.
        if str(item.get("player_match_confidence") or "").casefold()=="low":
            continue
        seen_players.add(player.casefold())
        candidates.append(item)
        if len(candidates)>=max(0,int(player_limit)):
            break

    searches=[]
    dedupe=set()
    for item in candidates:
        for row in build_search_matrix(item,category_name):
            key=(row["query"].casefold(),row["category_id"],row["order_by"])
            if key in dedupe:
                continue
            dedupe.add(key)
            searches.append(row)
            if len(searches)>=max(0,int(max_searches)):
                break
        if len(searches)>=max(0,int(max_searches)):
            break

    return {
        "category_name":category_name,
        "players_used":[_clean(i.get("player_name")) for i in candidates],
        "searches":searches,
        "search_count":len(searches),
        "creates_identity":False,
        "creates_value":False,
        "creates_buy_decision":False,
        "note":"Sökplanen hittar kandidater. Alla träffar måste analyseras med ordinarie FlipFynd-regler.",
    }


def tradera_api_readiness(env=None):
    env=os.environ if env is None else env
    app_id=_clean(env.get("TRADERA_APP_ID"))
    app_key=_clean(env.get("TRADERA_APP_KEY"))
    placeholder=app_key.casefold() in {"byt_den_här_nyckeln","change_me","placeholder"}
    ready=bool(app_id and app_key and not placeholder)
    return {
        "ready":ready,
        "app_id_present":bool(app_id),
        "app_key_present":bool(app_key and not placeholder),
        "reason":"Tradera API-uppgifter finns." if ready else "TRADERA_APP_ID och TRADERA_APP_KEY krävs för automatisk API-sökning.",
    }
