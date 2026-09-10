"""Active Supply Intelligence.

Read-only verification layer for Market Gap candidates. It queries Tradera with
structured player names and reports observed active search-result counts from the
API response pages actually fetched. It never extrapolates to the whole market.
"""
from __future__ import annotations
from src.tradera_api_search import search_once


CATEGORY_IDS={"Hockey - NHL":293316,"Fotboll":293311}


def build_supply_query(player_name):
    player=str(player_name or "").strip()
    if not player:
        return None
    return player


def verify_active_supply(row, *, app_id, app_key, category_name, pages=2):
    query=build_supply_query((row or {}).get("player_name"))
    category_id=CATEGORY_IDS.get(category_name)
    if not query or not category_id:
        return {
            "ok":False,"status":"NOT_READY","observed_unique_items":0,
            "pages_checked":0,"creates_buy_decision":False,"creates_value":False,
        }

    unique={}
    reports=[]
    for page in range(1,max(1,min(int(pages),3))+1):
        result=search_once(
            app_id=app_id,app_key=app_key,query=query,
            category_id=category_id,category_name=category_name,
            page_number=page,order_by="Relevance",query_kind="active-supply-check",
        )
        reports.append({"page":page,"status":result.get("status"),"count":len(result.get("items") or [])})
        if not result.get("ok"):
            continue
        for item in result.get("items") or []:
            key=item.get("tradera_item_id") or item.get("lank")
            if key:
                unique[str(key)]=item

    return {
        "ok":any(r["status"]=="OK" for r in reports),
        "status":"OK" if any(r["status"]=="OK" for r in reports) else "NO_SUCCESSFUL_PAGE",
        "query":query,
        "category_name":category_name,
        "observed_unique_items":len(unique),
        "pages_checked":len(reports),
        "page_reports":reports,
        "scope_note":"Observerat antal i de Tradera-sidor som faktiskt kontrollerades; inte hela marknadens totalutbud.",
        "creates_buy_decision":False,
        "creates_value":False,
        "creates_max_price":False,
    }


def classify_verified_supply(result):
    """Descriptive evidence label only; no BUY implication."""
    if not (result or {}).get("ok"):
        return "EJ_VERIFIERAT"
    n=int((result or {}).get("observed_unique_items") or 0)
    if n <= 2:
        return "FÅ_OBSERVERADE_TRÄFFAR"
    if n <= 10:
        return "BEGRÄNSAT_OBSERVERAT_UTBUD"
    return "FLERA_OBSERVERADE_TRÄFFAR"
