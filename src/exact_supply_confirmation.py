"""Exact Supply Confirmation.

Classifies already-analyzed Tradera search candidates against a target card's
existing Exact Identity Gate. No title guessing, no valuation, no BUY decision.
"""
from __future__ import annotations

from src.exact_identity_gate import build_exact_identity_gate


CRITICAL_FIELDS=("player_name","set_name","season","card_number")
OPTIONAL_EXACT_FIELDS=("parallel","grading_company","grade","serial_denominator")


def _clean(v):
    return " ".join(str(v or "").split()).strip().casefold()


def _identity(item):
    gate=build_exact_identity_gate(item or {})
    return gate, gate.get("identity_fields") or {}


def classify_candidate_against_target(target, candidate):
    target_gate,target_fields=_identity(target)
    cand_gate,cand_fields=_identity(candidate)

    if not target_gate.get("supports_exact_comp_search"):
        return {
            "status":"TARGET_NOT_READY",
            "label":"Målkortets identitet är inte redo",
            "exact_match":False,
            "possible_match":False,
            "explicit_mismatch":False,
            "creates_value":False,
            "creates_buy_decision":False,
        }

    mismatches=[]
    missing=[]
    matches=[]

    for field in CRITICAL_FIELDS:
        tv=_clean(target_fields.get(field))
        cv=_clean(cand_fields.get(field))
        if not cv:
            missing.append(field)
        elif cv==tv:
            matches.append(field)
        else:
            mismatches.append(field)

    for field in OPTIONAL_EXACT_FIELDS:
        tv=_clean(target_fields.get(field))
        if not tv:
            continue
        cv=_clean(cand_fields.get(field))
        if not cv:
            missing.append(field)
        elif cv==tv:
            matches.append(field)
        else:
            mismatches.append(field)

    explicit_conflict=bool(mismatches)
    cand_exact_ready=bool(cand_gate.get("supports_exact_comp_search"))

    if explicit_conflict:
        status="WRONG_CARD"
        label="Fel kort / identitetskonflikt"
        exact=False
        possible=False
    elif cand_exact_ready and not missing:
        status="CONFIRMED_EXACT"
        label="Bekräftad exakt match"
        exact=True
        possible=False
    else:
        status="POSSIBLE_MATCH"
        label="Möjlig match – mer identitet krävs"
        exact=False
        possible=True

    return {
        "status":status,
        "label":label,
        "exact_match":exact,
        "possible_match":possible,
        "explicit_mismatch":explicit_conflict,
        "matching_fields":matches,
        "missing_fields":missing,
        "mismatch_fields":mismatches,
        "candidate_exact_ready":cand_exact_ready,
        "creates_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
    }


def build_confirmation_report(target, analyzed_items):
    target_gate,target_fields=_identity(target)
    if not target_gate.get("supports_exact_comp_search"):
        return {
            "ready":False,
            "status":"TARGET_NOT_READY",
            "confirmed_exact":0,
            "possible":0,
            "wrong_card":0,
            "rows":[],
            "creates_value":False,
            "creates_buy_decision":False,
        }

    target_query=str((target or {}).get("search_expansion_query") or "").strip().casefold()
    rows=[]
    seen=set()
    for item in analyzed_items or []:
        if not isinstance(item,dict):
            continue
        # Confirmation is only for candidates that came from exact-card supply search.
        if item.get("search_expansion_kind")!="exact-card-supply-query":
            continue
        if target_query:
            item_query=str(item.get("search_expansion_query") or "").strip().casefold()
            if item_query != target_query:
                continue
        marker=item.get("tradera_item_id") or item.get("lank") or item.get("url")
        marker=str(marker) if marker else None
        if marker and marker in seen:
            continue
        if marker:
            seen.add(marker)
        verdict=classify_candidate_against_target(target,item)
        rows.append({
            "marker":marker,
            "title":item.get("titel") or item.get("title"),
            "player_name":(build_exact_identity_gate(item).get("identity_fields") or {}).get("player_name"),
            **verdict,
        })

    confirmed=sum(1 for r in rows if r["status"]=="CONFIRMED_EXACT")
    possible=sum(1 for r in rows if r["status"]=="POSSIBLE_MATCH")
    wrong=sum(1 for r in rows if r["status"]=="WRONG_CARD")
    return {
        "ready":True,
        "status":"OK",
        "confirmed_exact":confirmed,
        "possible":possible,
        "wrong_card":wrong,
        "rows":rows,
        "creates_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
        "note":"Bekräftad exakt match kräver att även kandidaten passerar Exact Identity Gate och matchar alla relevanta strukturerade identitetsfält.",
    }
