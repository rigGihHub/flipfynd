"""Shared helpers for ordinary FlipFynd analysis.

Kept free of Streamlit so the same primitives can be used by the web UI and a
background worker. Moving these helpers first avoids a forked analysis engine.
"""
from __future__ import annotations

import hashlib
import json
import re

from src.analyzer import analyze_item


def normalize_text(text):
    if text is None:
        return ""
    text=str(text).lower().replace("-"," ").replace("\n"," ").replace("\r"," ")
    text=text.replace("youngguns","young guns")
    return re.sub(r"\s+"," ",text).strip()


def matches_search(value, search):
    search=normalize_text(search)
    if not search:
        return True
    value=normalize_text(value)
    if search in value:
        return True
    return all(word in value for word in search.split())


def item_matches_search(item, search):
    return matches_search(item.get("titel",""),search) or matches_search(item.get("raw_text",""),search)


def infer_item_sport(item):
    source=str(item.get("source_category","")).lower()
    if "fotboll" in source or "football" in source:
        return "football"
    if "hockey" in source or "nhl" in source:
        return "hockey"
    return None


def get_seller(item):
    for key in ("saljare","säljare","seller","seller_name","username"):
        value=item.get(key)
        if value and str(value).strip():
            return str(value).strip()
    return "Okänd"


def detect_sale_type(item):
    text=" ".join(str(item.get(k) or "") for k in ("sale_type","raw_text","titel","title")).casefold()
    explicit=str(item.get("sale_type") or "").casefold()
    if "auktion" in explicit:
        return "Auktion"
    if "köp nu" in explicit or "buy it now" in explicit:
        return "Köp nu"
    if "köp nu" in text:
        return "Köp nu"
    if "utropspris" in text or "ledande bud" in text or " bud" in text:
        return "Auktion"
    return "Okänd"


def _feature_text(item):
    return " ".join(str(item.get(k) or "") for k in ("titel","title","raw_text","full_description")).casefold()


def is_numbered(item):
    text=_feature_text(item)
    return bool(re.search(r"(?<!\d)\d{1,4}\s*/\s*\d{1,4}(?!\d)|\b(?:numbered|numrerad)\b",text))


def is_patch(item):
    text=_feature_text(item)
    return bool(re.search(r"\b(?:patch|relic|memorabilia|jersey|game[- ]used|player[- ]worn)\b",text))


def is_auto(item):
    text=_feature_text(item)
    if re.search(r"\b(?:facsimile|printed|pre[- ]?printed|signature style)\b",text):
        return False
    return bool(re.search(r"\b(?:auto|autograph|autographed|hard[- ]signed|on[- ]card)\b",text))


def fast_signature(item, sport, strategy):
    payload={
        "url":item.get("url") or item.get("link"),
        "title":item.get("titel") or item.get("title"),
        "price":item.get("pris"),"shipping":item.get("frakt"),
        "raw_text":item.get("raw_text"),"full_description":item.get("full_description"),
        "sport":sport,"strategy":strategy,
    }
    return hashlib.sha1(json.dumps(payload,sort_keys=True,ensure_ascii=False,default=str).encode("utf-8")).hexdigest()


def fast_analysis(item, sport, strategy):
    return analyze_item(item,mode="fast",strategy_mode=strategy,sport=sport)


__all__=["normalize_text","matches_search","item_matches_search","infer_item_sport","get_seller","detect_sale_type","is_numbered","is_patch","is_auto","fast_signature","fast_analysis"]
