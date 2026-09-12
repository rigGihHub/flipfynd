"""Low-friction exact-comp research helpers.

This module deliberately separates two things:
1) direct realised sales, which may become exact SOLD comps only after explicit
   human verification, and
2) price-guide context, which can never become a SOLD comp by itself.

No external marketplace HTML is scraped. SportsCardsPro access uses its
published premium API only when the user has configured a token.
"""
from __future__ import annotations

import os
from urllib.parse import quote_plus

import requests

from src.comp_source_intelligence import exact_identity_query, ebay_sold_url_for_query
from src.sold_research_assist import build_exact_research_query, build_manual_sold_row

SPORTSCARDSPRO_API_URL = "https://www.sportscardspro.com/api/product"


def _clean(value) -> str:
    return " ".join(str(value or "").strip().split())


def build_research_links(identity: dict | None) -> dict:
    """Build safe direct research links from structured identity only."""
    identity = identity or {}
    exact = build_exact_research_query(identity)
    query = exact.get("query") or exact_identity_query(identity)
    if not query:
        return {"ready": False, "query": None, "links": [], "missing_fields": exact.get("missing_fields") or []}

    encoded = quote_plus(query)
    links = [
        {"key": "tradera", "label": "Tradera", "url": f"https://www.tradera.com/search?q={encoded}", "role": "LOCAL_MARKET"},
        {"key": "ebay", "label": "eBay Sold", "url": ebay_sold_url_for_query(query), "role": "DIRECT_SOLD"},
        {
            "key": "sportscardspro",
            "label": "SportsCardsPro",
            "url": f"https://www.sportscardspro.com/search-products?exclude-variants=false&q={encoded}&region-name=all&type=prices&view=grid",
            "role": "PRICE_GUIDE_CONTEXT",
        },
        {"key": "card_ladder", "label": "Card Ladder", "url": "https://www.cardladder.com/", "role": "MULTI_MARKET"},
        {"key": "fanatics", "label": "Fanatics Collect", "url": "https://sales-history.fanaticscollect.com/", "role": "DIRECT_SOLD"},
        {"key": "comc", "label": "COMC", "url": "https://www.comc.com/", "role": "MARKET_CONTEXT"},
        {"key": "130point", "label": "130 Point", "url": "https://130point.com/", "role": "SALES_RESEARCH"},
    ]
    return {"ready": bool(exact.get("ready")), "query": query, "links": links, "missing_fields": exact.get("missing_fields") or []}


def sportscardspro_api_configured(token: str | None = None) -> bool:
    return bool(_clean(token or os.getenv("SPORTSCARDSPRO_TOKEN")))


def fetch_sportscardspro_context(identity: dict | None, *, token: str | None = None, timeout: float = 12.0) -> dict:
    """Fetch current SportsCardsPro guide context using the documented API.

    Historic sales are not returned by this API, so the result is explicitly
    tagged as context-only and must never be fed into exact SOLD counts.
    """
    query = exact_identity_query(identity or {})
    if not query:
        return {"ok": False, "status": "IDENTITY_NOT_READY", "error": "Strukturerad kortidentitet saknas."}
    api_token = _clean(token or os.getenv("SPORTSCARDSPRO_TOKEN"))
    if not api_token:
        return {"ok": False, "status": "TOKEN_MISSING", "error": "SPORTSCARDSPRO_TOKEN är inte konfigurerad."}

    response = requests.get(
        SPORTSCARDSPRO_API_URL,
        params={"t": api_token, "q": query},
        timeout=timeout,
        headers={"User-Agent": "FlipFynd/comp-research"},
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        return {"ok": False, "status": "API_ERROR", "error": payload.get("error-message") or "SportsCardsPro API returnerade fel."}

    def cents(key):
        value = payload.get(key)
        try:
            return None if value in (None, "") else round(float(value) / 100.0, 2)
        except (TypeError, ValueError):
            return None

    return {
        "ok": True,
        "status": "CONTEXT_ONLY",
        "query": query,
        "product_id": payload.get("id"),
        "product_name": payload.get("product-name"),
        "set_name": payload.get("console-name"),
        "ungraded_usd": cents("loose-price"),
        "grade_7_usd": cents("grade-7-price"),
        "grade_8_usd": cents("grade-8-price"),
        "grade_9_usd": cents("grade-9-price"),
        "psa_10_usd": cents("new-price"),
        "note": "SportsCardsPro API ger aktuella guidevärden, inte historiska individuella sales. Resultatet får aldrig räknas som exact SOLD.",
    }


def parse_verified_sales_batch(
    text: str,
    identity: dict,
    *,
    identity_verified: bool,
    identity_evidence_source: str,
    sales_confirmed: bool,
) -> dict:
    """Parse several manually verified sales with minimal repetitive typing.

    Expected line format:
      source | sold_price | currency | fx_rate_to_sek | sold_at | url

    `fx_rate_to_sek` may be blank for SEK rows. Every row is still routed
    through build_manual_sold_row, so all existing strict verification rules
    remain in force.
    """
    if not identity_verified:
        return {"rows": [], "errors": ["Bekräfta att exakt kortidentitet är verifierad."], "valid_count": 0}
    if not sales_confirmed:
        return {"rows": [], "errors": ["Bekräfta att varje rad är en faktisk genomförd försäljning."], "valid_count": 0}

    rows = []
    errors = []
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip() and not line.lstrip().startswith("#")]
    for line_no, line in enumerate(lines, start=1):
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 3:
            errors.append(f"Rad {line_no}: minst source | price | currency krävs.")
            continue
        parts += [""] * (6 - len(parts))
        source, price, currency, fx_rate, sold_at, url = parts[:6]
        try:
            row = build_manual_sold_row(
                identity,
                sold_price=price,
                currency=currency,
                source_platform=source,
                sold_url=url,
                sold_at=sold_at,
                fx_rate_to_sek=(fx_rate or None),
                identity_verified=True,
                identity_evidence_source=identity_evidence_source,
                sale_confirmed=True,
            )
            rows.append(row)
        except ValueError as exc:
            errors.append(f"Rad {line_no}: {exc}")
    return {"rows": rows, "errors": errors, "valid_count": len(rows), "line_count": len(lines)}
