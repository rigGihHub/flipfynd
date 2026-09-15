"""Official eBay Browse API context for active listings only."""
from __future__ import annotations

import base64
from functools import lru_cache
import json
import os
import re
import statistics
from urllib.parse import quote_plus

import requests

from src.research_candidate_matcher import match_research_candidate

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def _literal_identity_hints(identity, row):
    """Expose only target values that are literally present in an eBay title."""
    out = dict(row)
    title = str(row.get("title") or "")
    normalized = re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()
    for key in ("player_name", "season", "set_name", "card_number", "parallel", "grading_company", "grade"):
        value = str((identity or {}).get(key) or "").strip()
        needle = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
        if needle and needle in normalized:
            out[key] = value
    denominator = str((identity or {}).get("serial_denominator") or "").strip()
    if denominator and re.search(rf"/\s*{re.escape(denominator)}(?!\d)", title):
        out["serial_denominator"] = denominator
    return out


def configured_credentials():
    client_id = str(os.getenv("EBAY_CLIENT_ID") or "").strip()
    client_secret = str(os.getenv("EBAY_CLIENT_SECRET") or "").strip()
    if not (client_id and client_secret):
        try:
            import streamlit as st
            client_id = client_id or str(st.secrets.get("EBAY_CLIENT_ID") or "").strip()
            client_secret = client_secret or str(st.secrets.get("EBAY_CLIENT_SECRET") or "").strip()
        except Exception:
            pass
    return client_id, client_secret


def fetch_ebay_active_context(query, *, identity=None, client_id, client_secret, session=requests, timeout=12, limit=25):
    query = " ".join(str(query or "").split())
    if not query:
        return {"ok": False, "status": "QUERY_MISSING"}
    if not str(client_id or "").strip() or not str(client_secret or "").strip():
        return {"ok": False, "status": "CREDENTIALS_MISSING"}
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    token_response = session.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"},
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        timeout=timeout,
    )
    token_response.raise_for_status()
    token = token_response.json().get("access_token")
    if not token:
        return {"ok": False, "status": "TOKEN_MISSING"}
    response = session.get(
        SEARCH_URL,
        params={"q": query, "limit": max(1, min(int(limit), 50))},
        headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    raw_rows = []
    for item in payload.get("itemSummaries") or []:
        price = item.get("price") or {}
        try:
            value = float(price.get("value"))
        except (TypeError, ValueError):
            continue
        raw_rows.append({"title": item.get("title"), "price": value, "currency": price.get("currency"), "url": item.get("itemWebUrl"), "source": "eBay Browse"})
    rows = []
    for row in raw_rows:
        candidate = _literal_identity_hints(identity or {}, row)
        match = match_research_candidate(identity or {}, candidate)
        if match["label"] not in {"STRONG_CANDIDATE", "REVIEW"}:
            continue
        row = dict(row)
        row["match_label"] = match["label"]
        row["match_confidence"] = match["candidate_confidence"]
        row["matches"] = match["matches"]
        rows.append(row)
    usd = [row["price"] for row in rows if row.get("currency") == "USD"]
    return {
        "ok": True,
        "status": "ACTIVE_CONTEXT_ONLY",
        "query": query,
        "raw_listing_count": len(raw_rows),
        "listing_count": len(rows),
        "rejected_listing_count": len(raw_rows) - len(rows),
        "min_usd": min(usd) if usd else None,
        "median_usd": round(statistics.median(usd), 2) if usd else None,
        "max_usd": max(usd) if usd else None,
        "rows": rows[:5],
        "search_url": f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}",
        "sold_comps": 0,
        "context_only": True,
        "note": "Endast identitetsmatchade aktiva eBay-annonser, inte genomförda försäljningar. Påverkar inte KÖP, marknadsvärde eller maxbud.",
    }


@lru_cache(maxsize=256)
def _fetch_configured_cached(query, identity_json):
    identity = json.loads(identity_json) if identity_json else {}
    client_id, client_secret = configured_credentials()
    return fetch_ebay_active_context(query, identity=identity, client_id=client_id, client_secret=client_secret)


def fetch_configured_ebay_active_context(query, identity=None):
    """Cached production entrypoint so one rerun does not repeat API calls."""
    identity_json = json.dumps(identity or {}, sort_keys=True, ensure_ascii=False, default=str)
    return _fetch_configured_cached(query, identity_json)
