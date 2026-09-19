"""Official eBay Browse API context for active listings only."""
from __future__ import annotations

import base64
from functools import lru_cache
import hashlib
import json
import os
import re
import statistics
import time
from datetime import datetime, timezone
from math import isfinite
from urllib.parse import quote_plus

import requests

from src.research_candidate_matcher import match_research_candidate
from src.card_parser import parse_card_features
from src.card_listing_integrity import assess_listing_integrity

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def _literal_identity_hints(identity, row):
    """Expose only target values that are literally present in an eBay title."""
    out = dict(row)
    title = str(row.get("title") or "")
    parsed = parse_card_features(title)
    normalized = re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()
    for key in ("player_name", "season", "set_name", "card_number", "parallel", "grading_company", "grade"):
        # A target number elsewhere in a title (for example a PSA grade) must
        # not overwrite a different card number actually parsed from it.
        if key in {"card_number", "season", "parallel", "grading_company", "grade"} and parsed.get(key):
            continue
        value = str((identity or {}).get(key) or "").strip()
        needle = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
        if needle and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", normalized):
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


_TOKEN_CACHE = {}


def fetch_ebay_active_context(query, *, identity=None, client_id, client_secret, session=requests, timeout=5, limit=25):
    query = " ".join(str(query or "").split())
    if not query:
        return {"ok": False, "status": "QUERY_MISSING"}
    if not str(client_id or "").strip() or not str(client_secret or "").strip():
        return {"ok": False, "status": "CREDENTIALS_MISSING"}
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    cache_key = (client_id, client_secret)
    cached_token = _TOKEN_CACHE.get(cache_key) if session is requests else None
    token = cached_token[0] if cached_token and cached_token[1] > time.monotonic() else None
    if not token:
        token_response = session.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"},
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
            timeout=timeout,
        )
        if not token_response.ok:
            err = requests.HTTPError(f"EBAY_TOKEN_HTTP_{token_response.status_code}", response=token_response)
            setattr(err, "ebay_stage", "TOKEN")
            raise err
        token_data = token_response.json()
        token = token_data.get("access_token")
        if token and session is requests:
            _TOKEN_CACHE.clear()
            _TOKEN_CACHE[cache_key] = (token, time.monotonic() + max(0, float(token_data.get("expires_in") or 7200) - 60))
    if not token:
        return {"ok": False, "status": "TOKEN_MISSING"}
    response = session.get(
        SEARCH_URL,
        params={"q": query, "limit": max(1, min(int(limit), 50)), "filter": "buyingOptions:{FIXED_PRICE}"},
        headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"},
        timeout=timeout,
    )
    if not response.ok:
        err = requests.HTTPError(f"EBAY_BROWSE_HTTP_{response.status_code}", response=response)
        setattr(err, "ebay_stage", "BROWSE")
        raise err
    payload = response.json()
    raw_rows = []
    for item in payload.get("itemSummaries") or []:
        price = item.get("price") or {}
        try:
            value = float(price.get("value"))
        except (TypeError, ValueError):
            continue
        if not isfinite(value) or value <= 0:
            continue
        # Keep item price strictly separate from shipping. Browse API's
        # price field is the listing/item price; shipping is diagnostic only
        # and must never inflate the card's comparison value.
        shipping_options = item.get("shippingOptions") or []
        shipping_cost = None
        if shipping_options:
            cost = (shipping_options[0] or {}).get("shippingCost") or {}
            try:
                shipping_cost = float(cost.get("value")) if cost.get("value") is not None else None
            except (TypeError, ValueError):
                shipping_cost = None
        raw_rows.append({
            "title": item.get("title"), "price": value,
            "item_price": value, "currency": price.get("currency"),
            "shipping_price": shipping_cost,
            "url": item.get("itemWebUrl"), "source": "eBay Browse",
            "buying_options": item.get("buyingOptions") or [], "item_id": item.get("itemId")
        })
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
        parsed = parse_card_features(str(row.get("title") or ""))
        integrity = assess_listing_integrity(row)
        target_graded = bool((identity or {}).get("grading_company") or (identity or {}).get("grade"))
        candidate_graded = bool(parsed.get("grading_company") or parsed.get("grade")
                                or re.search(r"\b(?:PSA|BGS|BVG|SGC|CGC|CSG|KSA|TAG)\b", str(row.get("title") or ""), re.I))
        extra_serial = bool(parsed.get("serial_number") and not (identity or {}).get("serial_denominator"))
        row["asking_comparison_eligible"] = bool(
            match["label"] == "STRONG_CANDIDATE" and not match["missing"] and not match["conflicts"]
            and target_graded == candidate_graded and not extra_serial
            and (not target_graded or ((identity or {}).get("grade") and (identity or {}).get("grading_company")))
            and "FIXED_PRICE" in row["buying_options"]
            and integrity["eligible_physical_single_card"] and not integrity["reprint_risk"]
            and not parsed.get("is_lot")
        )
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
        "rows": rows,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "search_url": f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}",
        "sold_comps": 0,
        "context_only": True,
        "note": "Aktiva eBay-annonser används för begärda prisjämförelser och möjliga fynd. De är inte SOLD eller verifierat försäljningsvärde.",
    }


@lru_cache(maxsize=256)
def _fetch_configured_cached(query, identity_json, cache_period):
    identity = json.loads(identity_json) if identity_json else {}
    client_id, client_secret = configured_credentials()
    return fetch_ebay_active_context(query, identity=identity, client_id=client_id, client_secret=client_secret)


def _persistent_cache_key(query, identity_json):
    raw = f"{query}\n{identity_json}".encode("utf-8", errors="ignore")
    return "ebay_active:" + hashlib.sha256(raw).hexdigest()


def _persistent_get(key, max_age_seconds=900):
    """Best-effort cross-session cache when Postgres is configured."""
    try:
        import psycopg
        dsn = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
        if not dsn:
            return None
        with psycopg.connect(dsn) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS flipfynd_market_cache (
                cache_key TEXT PRIMARY KEY, payload JSONB NOT NULL,
                fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
            row = conn.execute(
                """SELECT payload FROM flipfynd_market_cache
                   WHERE cache_key=%s AND fetched_at > NOW() - (%s * INTERVAL '1 second')""",
                (key, int(max_age_seconds)),
            ).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _persistent_put(key, payload):
    try:
        import psycopg
        dsn = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
        if not dsn:
            return
        with psycopg.connect(dsn) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS flipfynd_market_cache (
                cache_key TEXT PRIMARY KEY, payload JSONB NOT NULL,
                fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
            conn.execute(
                """INSERT INTO flipfynd_market_cache(cache_key,payload,fetched_at)
                   VALUES (%s,%s::jsonb,NOW())
                   ON CONFLICT(cache_key) DO UPDATE
                   SET payload=EXCLUDED.payload,fetched_at=NOW()""",
                (key, json.dumps(payload, ensure_ascii=False, default=str)),
            )
    except Exception:
        pass


def fetch_configured_ebay_active_context(query, identity=None):
    """Fetch eBay context for the current analysis only.

    Compliance rule: do not persist or cross-session cache eBay response data.
    The OAuth token cache remains in-process only and contains no listing data.
    """
    identity_json = json.dumps(identity or {}, sort_keys=True, ensure_ascii=False, default=str)
    identity_obj = json.loads(identity_json) if identity_json else {}
    client_id, client_secret = configured_credentials()
    return fetch_ebay_active_context(
        query,
        identity=identity_obj,
        client_id=client_id,
        client_secret=client_secret,
    )
