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


__all__=["normalize_text","matches_search","item_matches_search","infer_item_sport","get_seller","fast_signature","fast_analysis"]
