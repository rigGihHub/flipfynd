"""Rank the best current FlipFynd card candidates from one Tradera seller."""
from __future__ import annotations
from typing import Callable, Iterable
from src.seller_card_domain import seller_item_domain_check
from src.seller_live_quick_analysis import quick_analyze_seller_inventory
from src.seller_live_full_analysis import full_analyze_live_seller_item
from src.card_parser import parse_card_features
from src.adaptive_deepening import select_dynamic_seller_deep_rows
from src.seller_card_merit import assess_seller_card_merit
from src.fast_analysis_pool import select_fast_analysis_pool
from src.analysis_budget import fast_analysis_budget
from src.deal_readiness import assess_deal_readiness

HIDDEN_FIND_EXPLORATION_SLOTS=4

def _emit(callback,**payload):
    if callable(callback):
        try: callback(dict(payload))
        except Exception: pass

def _num(value,default=0.0):
    try:return float(value)
    except (TypeError,ValueError):return float(default)

def _identity_key(item):
    for key in ("tradera_item_id","id","item_id","lank","url","link"):
        value=item.get(key)
        if value not in (None,""):return str(value).strip()
    return str(item.get("titel") or item.get("title") or "").strip().casefold()

def _card_opportunity_key(row):
    source=row.get("source_item") or row; title=str(source.get("titel") or source.get("title") or row.get("title") or "").strip(); features=parse_card_features(title)
    identity=tuple(str(features.get(key) or "").strip().casefold() for key in ("season","set_name","card_number","player_name","parallel","grading_company","grade"))
    if identity[0] and identity[1] and identity[2] and identity[3]:return "card:"+"|".join(identity)
    return "listing:"+_identity_key(source)

def _explicit_condition_risk(row):
    source=row.get("source_item") or row; text=" ".join(str(source.get(key) or row.get(key) or "") for key in ("titel","title","description","full_description")).casefold()
    return any(token in text for token in ("märken på","skadad","skador","dåligt skick","poor condition","crease","creased","veck","repor","repa","corner damage","kantstött","kantstötning"))

def _select_diverse_rows(rows,limit=5):
    clean,condition_risk=[],[]; seen=set(); duplicate_count=0
    for row in rows:
        key=_card_opportunity_key(row)
        if key in seen:duplicate_count+=1;continue
        seen.add(key); (condition_risk if _explicit_condition_risk(row) else clean).append(row)
    selected=clean[:limit]
    if len(selected)<limit:
        for raw in condition_risk[:limit-len(selected)]:
            row=dict(raw); row["condition_risk"]=True; row["label"]="SKICKRISK · BÄST AV RESTEN"; selected.append(row)
    return selected,duplicate_count,len(condition_risk)

def _supported_sport(item,fallback="hockey"):
    text=" ".join(str(item.get(key) or "") for key in ("titel","title","source_category","category_name","category","breadcrumb","path","raw_text","full_description","description")).casefold()
    football=("fotboll","football","soccer","premier league","champions league","uefa","fifa","match attax","adrenalyn","la liga","serie a","bundesliga","world cup"); hockey=("hockey","nhl","upper deck","o-pee-chee","opc","young guns","ice hockey","shl")
    fh=sum(x in text for x in football); hh=sum(x in text for x in hockey)
    if fh>hh:return "football"
    if hh>fh:return "hockey"
    return fallback if fallback in {"hockey","football"} else "hockey"

def _ordinary_rank_key(row):return (_num(row.get("rank_score")),_num(row.get("player_market_score")),_num(row.get("risk_adjusted_profit")))

def _seller_opportunity_score(row):
    collector=min(40.0,_num(row.get("collector_signal_score"))); merit=assess_seller_card_merit(row); deal=_num(row.get("deal_score")); profit=_num(row.get("risk_adjusted_profit")); sold=int(_num(row.get("sold_comps")))
    score=deal*.55+_num(row.get("rank_score"))*.25+merit["score"]*.15+collector*.05
    if deal<=10 and profit<=0 and sold==0:score=min(score,25.0)
    return round(max(0,min(100,score)),1)

def _seller_opportunity_rank_key(row):
    """Final Top-5 order: proven economics first; asking prices are discovery evidence."""
    decision=str(row.get("decision") or "").upper(); sold=int(_num(row.get("sold_comps"))); identity=bool(row.get("identity_ok")); deal=_num(row.get("deal_score")); profit=_num(row.get("risk_adjusted_profit")); asking=row.get("asking_price_opportunity") or {}; asking_find=bool(asking.get("possible_find")); readiness=assess_deal_readiness(row); merit=assess_seller_card_merit(row)
    verified_find=decision.startswith("KÖP") and readiness["ready_for_find"]
    verified_economics=identity and sold>0 and profit>0
    research=seller_result_tier(row)=="RESEARCH"
    # Asking-price comparisons can surface a possible find, even from one
    # seller, but cannot outrank a card with verified SOLD-backed economics.
    tier=4 if verified_find else 3 if verified_economics else 2 if asking_find else 1 if research else 0
    return (tier,profit if tier>=3 else 0,_num(asking.get("net_margin")) if asking_find else 0,sold,deal,_seller_opportunity_score(row),merit["score"],_num(row.get("rank_score")),_num(row.get("player_market_score")))

def _quick_rank_key(row):
    sold=int(_num(row.get("sold_comps"))); identity=bool(row.get("identity_ok")); profit=_num(row.get("risk_adjusted_profit")); decision=str(row.get("decision") or "").upper(); evidence=2 if identity and sold>0 else 1 if identity else 0; econ=2 if profit>0 and sold>0 else 1 if profit>0 else 0; buy=1 if decision.startswith("KÖP") and evidence==2 and econ==2 else 0
    return (-buy,-econ,-evidence,-profit,-sold,-_num(row.get("deal_score")),-_num(row.get("rank_score")),-_num(row.get("quick_score")),-_num(row.get("player_market_score")),-_num(row.get("collector_signal_score")),_num(row.get("price"),10**12))

def _seller_presentation_label(row):
    out=dict(row); decision=str(out.get("decision") or "SKIP").upper()
    if decision.startswith("KÖP") and assess_deal_readiness(out)["ready_for_find"]:out["label"]="KÖP-KANDIDAT"
    elif (out.get("asking_price_opportunity") or {}).get("possible_find"):out["label"]="MÖJLIGT FYND · BEGÄRDA PRISER"
    elif decision.startswith(("KÖP","UNDERSÖK")):out["label"]="VÄRT ATT UNDERSÖKA"
    else:out["label"]="BÄST AV RESTEN"
    return out

def seller_result_tier(row):
    decision=str(row.get("decision") or "SKIP").upper(); readiness=assess_deal_readiness(row)
    if decision.startswith("KÖP") and readiness["ready_for_find"]:return "FIND"
    if decision.startswith("KÖP") or (row.get("asking_price_opportunity") or {}).get("possible_find"):return "RESEARCH"
    merit=assess_seller_card_merit(row)
    if merit["eligible"] and (decision.startswith("UNDERSÖK") or merit["score"]>=25 or (merit["strong_signals"] and merit["score"]>=18)):return "RESEARCH"
    return "WEAK"

def seller_result_badge(row):
    if seller_result_tier(row)=="FIND":return "🟢 KÖP"
    if str(row.get("decision") or "").upper().startswith(("KÖP","UNDERSÖK")):return "🟡 Värt att undersöka"
    return "⚪ Kandidat · ej verifierad"

def _quick_scan_inventory(alias,inventory,*,analyze_fn,sport,quick_limit,progress_callback=None):
    anchor={"saljare":alias,"tradera_item_id":"__seller_top5_anchor__"}; batch_size=max(20,min(int(quick_limit or 60),100)); unique={}
    for row in inventory:
        key=_identity_key(row)
        if key:unique[key]=row
    unique_inventory=list(unique.values()); fast_pool=select_fast_analysis_pool(unique_inventory,cap=fast_analysis_budget(len(unique_inventory),context="seller"),exploration_fraction=.30); groups={"hockey":[],"football":[]}
    for row in fast_pool:groups[_supported_sport(row,fallback=sport)].append(row)
    all_rows={}; failed=batches=domain_rejected=analysed_so_far=0; total=len(fast_pool); _emit(progress_callback,phase="quick_start",done=0,total=total,percent=28)
    for group_sport in ("hockey","football"):
        group=groups[group_sport]
        for start in range(0,len(group),batch_size):
            batch=group[start:start+batch_size]
            if not batch:continue
            batches+=1; quick=quick_analyze_seller_inventory(anchor,batch,analyze_fn=analyze_fn,sport=group_sport,strategy_mode="quick_flip",limit=len(batch),shortlist=min(5,len(batch))); failed+=int(quick.get("failed_count") or 0); domain_rejected+=int(quick.get("domain_rejected_count") or 0); analysed_so_far+=len(batch)
            for row in quick.get("rows") or []:
                source=row.get("source_item") or {}; row=dict(row); row["sport"]=group_sport; key=_identity_key(source) or _identity_key(row)
                if not key:continue
                previous=all_rows.get(key)
                if previous is None or _quick_rank_key(row)<_quick_rank_key(previous):all_rows[key]=row
            _emit(progress_callback,phase="quick_progress",done=min(analysed_so_far,total),total=total,percent=28+int(37*min(1,analysed_so_far/max(1,total))),sport=group_sport)
    rows=list(all_rows.values()); rows.sort(key=_quick_rank_key); _emit(progress_callback,phase="quick_complete",done=total,total=total,percent=65)
    return {"rows":rows,"analysed_count":len(rows),"failed_count":failed,"batch_count":batches,"domain_rejected_count":domain_rejected,"inventory_unique_count":len(unique_inventory),"cheap_coverage_complete":True,"fast_pool_count":len(fast_pool),"coverage_complete":len(rows)+failed+domain_rejected>=len(fast_pool),"sport_counts":{k:len(v) for k,v in groups.items()}}

def _fallback_row(qrow,alias):
    decision=str(qrow.get("decision") or "SKIP"); du=decision.upper(); label="KÖP-KANDIDAT · SNABBANALYS" if du.startswith("KÖP") else "VÄRT ATT UNDERSÖKA · SNABBANALYS" if du.startswith("UNDERSÖK") else "BÄST AV RESTEN · EJ VERIFIERAT FYND"
    return {"title":qrow.get("title"),"price":qrow.get("price"),"url":qrow.get("url"),"decision":decision,"label":label,"reason":"Reservresultat från snabbanalysen. Visas för att Top 5 alltid ska innehålla de fem bästa giltiga korten när minst fem finns.","identity_ok":qrow.get("identity_ok"),"sold_comps":qrow.get("sold_comps",0),"valuation_confidence":qrow.get("valuation_confidence",0),"market_edge":qrow.get("market_edge",0),"quick_score":qrow.get("quick_score",0),"deal_score":qrow.get("deal_score",0),"rank_score":qrow.get("rank_score",0),"player_market_score":qrow.get("player_market_score",0),"risk_adjusted_profit":qrow.get("risk_adjusted_profit",0),"sport":qrow.get("sport"),"seller":alias,"source_item":qrow.get("source_item") or {},"analysis_level":"quick_fallback"}

def _select_hidden_find_exploration(rows,*,exclude_keys=None,slots=4):
    exclude_keys=set(exclude_keys or set()); candidates=[]
    for position,row in enumerate(rows or []):
        key=_identity_key(row.get("source_item") or row)
        if not key or key in exclude_keys or assess_seller_card_merit(row)["eligible"]:continue
        source=row.get("source_item") or row
        if not assess_seller_card_merit(row)["integrity"]["eligible_physical_single_card"] or _explicit_condition_risk(row):continue
        title=str(source.get("titel") or source.get("title") or row.get("title") or "").strip(); warnings=list(source.get("listing_quality_warnings") or []); blockers=list(source.get("listing_quality_blockers") or []); quality=source.get("listing_quality_score")
        try:quality=float(quality) if quality is not None else None
        except (TypeError,ValueError):quality=None
        if not (warnings or blockers or (quality is not None and quality<55) or len(title)<36):continue
        candidates.append((len(warnings)+len(blockers)+(2 if quality is not None and quality<55 else 0)+(1 if len(title)<36 else 0),-_num(row.get("price"),10**12),position,row))
    candidates.sort(key=lambda v:(v[0],v[1],v[2]),reverse=True); selected=[]; seen=set()
    for _,_,_,raw in candidates:
        marked=dict(raw); marked["seller_deep_route"]="HIDDEN_FIND_EXPLORATION"; opportunity=_card_opportunity_key(marked)
        if opportunity in seen:continue
        selected.append(marked); seen.add(opportunity)
        if len(selected)>=max(0,int(slots or 0)):break
    return selected

def build_seller_top5(seller_alias,items,*,analyze_fn:Callable,sport="all",quick_limit=60,full_limit=10,progress_callback=None):
    alias=str(seller_alias or "").strip(); raw_inventory=[dict(x) for x in (items or []) if isinstance(x,dict)]
    if not alias:return {"status":"NO_SELLER","rows":[],"seller":None,"inventory_count":len(raw_inventory)}
    if not raw_inventory:return {"status":"NO_ITEMS","