"""Official eBay Browse API context for active listings only."""
from __future__ import annotations

import base64
from functools import lru_cache
import os
import statistics
from urllib.parse import quote_plus

import requests

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


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


def fetch_ebay_active_context(query, *, client_id, client_secret, session=requests, timeout=12, limit=25):
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
    rows = []
    for item in payload.get("itemSummaries") or []:
        price = item.get("price") or {}
        try:
            value = float(price.get("value"))
        except (TypeError, ValueError):
            continue
        rows.append({"title": item.get("title"), "price": value, "currency": price.get("currency"), "url": item.get("itemWebUrl")})
    usd = [row["price"] for row in rows if row.get("currency") == "USD"]
    return {
        "ok": True,
        "status": "ACTIVE_CONTEXT_ONLY",
        "query": query,
        "listing_count": len(rows),
        "min_usd": min(usd) if usd else None,
        "median_usd": round(statistics.median(usd), 2) if usd else None,
        "max_usd": max(usd) if usd else None,
        "rows": rows[:5],
        "search_url": f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}",
        "sold_comps": 0,
        "context_only": True,
        "note": "Aktiva eBay-annonser, inte genomförda försäljningar. Påverkar inte KÖP, marknadsvärde eller maxbud.",
    }


@lru_cache(maxsize=256)
def fetch_configured_ebay_active_context(query):
    """Cached production entrypoint so one rerun does not repeat API calls."""
    client_id, client_secret = configured_credentials()
    return fetch_ebay_active_context(query, client_id=client_id, client_secret=client_secret)
