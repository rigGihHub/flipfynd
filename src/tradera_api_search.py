"""Operational read-only Tradera REST v4 search integration.

Search/discovery only. Never bids, buys, values cards or infers missing identity.
The parser is deliberately fail-closed because v4 SearchResult is beta.
"""
from __future__ import annotations
import json
from pathlib import Path
import requests

SEARCH_URL="https://api.tradera.com/v4/search"


def _pick(d,*keys):
    for k in keys:
        if isinstance(d,dict) and d.get(k) is not None:
            return d.get(k)
    return None


def _num(v):
    try:
        return float(v)
    except (TypeError,ValueError):
        return None


def extract_search_rows(payload):
    if isinstance(payload,list):
        rows=payload
    elif isinstance(payload,dict):
        rows=None
        for key in ("items","Items","searchItems","SearchItems","results","Results"):
            if isinstance(payload.get(key),list):
                rows=payload[key]; break
        if rows is None:
            return []
    else:
        return []
    return [r for r in rows if isinstance(r,dict)]


def normalize_search_item(row, *, category_name, query, order_by, query_kind=None):
    item_id=_pick(row,"itemId","ItemId","id","Id")
    title=_pick(row,"title","Title","shortDescription","ShortDescription")
    if item_id is None or not str(title or "").strip():
        return None

    # Only explicit prices from API are accepted; no derivation from other fields.
    price=_pick(row,"price","Price","currentBid","CurrentBid","nextBid","NextBid","buyItNowPrice","BuyItNowPrice")
    price=_num(price)
    url=_pick(row,"itemUrl","ItemUrl","url","Url","link","Link")
    end_date=_pick(row,"endDate","EndDate")
    seller=_pick(row,"sellerAlias","SellerAlias","seller","Seller")
    if isinstance(seller,dict):
        seller=_pick(seller,"alias","Alias","name","Name")

    out={
        "titel":str(title).strip(),
        "pris":price,
        "frakt":None,
        "lank":str(url).strip() if url else None,
        "saljare":str(seller).strip() if seller else None,
        "slutdatum":end_date,
        "source_category":category_name,
        "source_type":"tradera_api_search_expansion",
        "tradera_item_id":str(item_id),
        "search_expansion_query":query,
        "search_expansion_order_by":order_by,
        "search_expansion_kind":query_kind,
        "search_expansion_candidate":True,
        "raw_api_item":row,
    }
    return out


def search_once(*, app_id, app_key, query, category_id, category_name, page_number=1, order_by="Relevance", query_kind=None, timeout=20):
    headers={"X-App-Id":str(app_id),"X-App-Key":str(app_key),"Accept":"application/json"}
    params={"query":query,"categoryId":int(category_id),"pageNumber":int(page_number),"orderBy":order_by}
    try:
        r=requests.get(SEARCH_URL,headers=headers,params=params,timeout=timeout)
    except requests.RequestException as exc:
        return {"ok":False,"status":"REQUEST_FAILED","error":str(exc),"items":[]}
    if r.status_code!=200:
        return {"ok":False,"status":"HTTP_ERROR","http_status":r.status_code,"error":"Tradera API returnerade fel.","items":[]}
    try:
        payload=r.json()
    except ValueError:
        return {"ok":False,"status":"INVALID_JSON","error":"Tradera API-svaret var inte giltig JSON.","items":[]}
    rows=extract_search_rows(payload)
    items=[]
    for row in rows:
        item=normalize_search_item(row,category_name=category_name,query=query,order_by=order_by,query_kind=query_kind)
        if item:
            items.append(item)
    return {"ok":True,"status":"OK","items":items,"raw_count":len(rows),"parsed_count":len(items)}


def run_search_plan(plan, *, app_id, app_key, max_searches=12):
    all_items=[]; reports=[]
    for row in (plan or {}).get("searches",[])[:max(0,int(max_searches))]:
        result=search_once(
            app_id=app_id,app_key=app_key,query=row["query"],
            category_id=row["category_id"],category_name=row["category_name"],
            page_number=row.get("page_number",1),order_by=row.get("order_by","Relevance"),
            query_kind=row.get("kind"),
        )
        reports.append({"query":row["query"],"order_by":row["order_by"],"status":result["status"],"parsed_count":len(result.get("items") or [])})
        all_items.extend(result.get("items") or [])

    dedup={}
    for item in all_items:
        key=("id",item.get("tradera_item_id")) if item.get("tradera_item_id") else ("url",item.get("lank"))
        if key[1]:
            dedup[key]=item
    return {
        "items":list(dedup.values()),
        "reports":reports,
        "searches_run":len(reports),
        "unique_items":len(dedup),
        "creates_buy_decision":False,
        "creates_value":False,
    }


def save_expansion_items(path, items):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    existing=[]
    if path.exists():
        try:
            data=json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data,list): existing=data
        except Exception:
            existing=[]
    merged={}
    for item in existing+list(items or []):
        if not isinstance(item,dict): continue
        key=item.get("tradera_item_id") or item.get("lank")
        if key: merged[str(key)]=item
    path.write_text(json.dumps(list(merged.values()),ensure_ascii=False,indent=2),encoding="utf-8")
    return len(merged)
