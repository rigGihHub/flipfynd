"""Exact Card Supply Check.

Uses the existing Exact Identity Gate to define an exact structured identity.
It can count already-analyzed exact matches and run a narrow Tradera discovery
query. API query hits are only candidates until they pass the same identity gate.
"""
from __future__ import annotations

from src.exact_identity_gate import build_exact_identity_gate
from src.tradera_api_search import search_once

CATEGORY_IDS={"Hockey - NHL":293316,"Fotboll":293311}


def _clean(v):
    return " ".join(str(v or "").split()).strip()


def exact_identity_key(item):
    gate=build_exact_identity_gate(item or {})
    if not gate.get("supports_exact_comp_search"):
        return None
    f=gate.get("identity_fields") or {}
    key=(
        _clean(f.get("player_name")).casefold(),
        _clean(f.get("set_name")).casefold(),
        _clean(f.get("season")).casefold(),
        _clean(f.get("card_number")).casefold(),
        _clean(f.get("parallel")).casefold(),
        _clean(f.get("grading_company")).casefold(),
        _clean(f.get("grade")).casefold(),
    )
    if not all(key[:4]):
        return None
    return key


def build_exact_supply_query(item):
    gate=build_exact_identity_gate(item or {})
    if not gate.get("supports_exact_comp_search"):
        return {
            "ready":False,
            "query":None,
            "status":"IDENTITY_NOT_READY",
            "blockers":gate.get("blockers") or gate.get("missing_fields") or [],
        }
    f=gate.get("identity_fields") or {}
    parts=[
        _clean(f.get("player_name")),
        _clean(f.get("set_name")),
        _clean(f.get("season")),
        _clean(f.get("card_number")),
    ]
    # Optional structured discriminators make the query narrower. They are never
    # invented and are omitted when not explicitly structured.
    for field in ("parallel","grading_company","grade"):
        value=_clean(f.get(field))
        if value:
            parts.append(value)
    return {
        "ready":True,
        "query":" ".join(p for p in parts if p),
        "status":"EXACT_QUERY_READY",
        "identity_fields":f,
        "supports_exact_comp_search":True,
    }


def count_analyzed_exact_matches(target, analyzed_items):
    target_key=exact_identity_key(target)
    if target_key is None:
        return {
            "ready":False,
            "exact_analyzed_matches":0,
            "match_ids":[],
            "creates_value":False,
            "creates_buy_decision":False,
        }
    match_ids=[]
    for item in analyzed_items or []:
        if not isinstance(item,dict):
            continue
        if exact_identity_key(item)==target_key:
            marker=item.get("tradera_item_id") or item.get("lank") or item.get("url")
            match_ids.append(str(marker) if marker else f"row-{len(match_ids)+1}")
    return {
        "ready":True,
        "exact_analyzed_matches":len(set(match_ids)),
        "match_ids":list(dict.fromkeys(match_ids)),
        "creates_value":False,
        "creates_buy_decision":False,
    }


def verify_exact_query_supply(item, *, app_id, app_key, category_name, pages=2):
    plan=build_exact_supply_query(item)
    category_id=CATEGORY_IDS.get(category_name)
    if not plan.get("ready") or not category_id:
        return {
            "ok":False,
            "status":"NOT_READY",
            "query":plan.get("query"),
            "observed_query_candidates":0,
            "pages_checked":0,
            "creates_value":False,
            "creates_buy_decision":False,
            "creates_max_price":False,
        }

    unique={}
    reports=[]
    for page in range(1,max(1,min(int(pages),3))+1):
        result=search_once(
            app_id=app_id,
            app_key=app_key,
            query=plan["query"],
            category_id=category_id,
            category_name=category_name,
            page_number=page,
            order_by="Relevance",
            query_kind="exact-card-supply-query",
        )
        reports.append({
            "page":page,
            "status":result.get("status"),
            "count":len(result.get("items") or []),
        })
        if result.get("ok"):
            for candidate in result.get("items") or []:
                key=candidate.get("tradera_item_id") or candidate.get("lank")
                if key:
                    unique[str(key)]=candidate

    ok=any(r["status"]=="OK" for r in reports)
    return {
        "ok":ok,
        "status":"OK" if ok else "NO_SUCCESSFUL_PAGE",
        "query":plan["query"],
        "observed_query_candidates":len(unique),
        "candidate_items":list(unique.values()),
        "pages_checked":len(reports),
        "page_reports":reports,
        "scope_note":(
            "Detta är träffar på en exakt strukturerad sökfråga. De är inte bekräftade "
            "exakta exemplar förrän de passerat FlipFynds vanliga identitetsanalys."
        ),
        "creates_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
    }
