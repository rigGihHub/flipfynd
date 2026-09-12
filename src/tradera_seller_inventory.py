"""Read-only Tradera seller inventory discovery via REST v4.

This module is intentionally discovery-only. It resolves a public seller alias to
an id and fetches that seller's active listings. It never bids, buys, values or
marks a listing as sold.
"""
from __future__ import annotations

from urllib.parse import quote
import requests

BASE_URL = "https://api.tradera.com/v4"


def _pick(d, *keys):
    for key in keys:
        if isinstance(d, dict) and d.get(key) is not None:
            return d.get(key)
    return None


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _headers(app_id, app_key):
    return {
        "X-App-Id": str(app_id),
        "X-App-Key": str(app_key),
        "Accept": "application/json",
    }


def _request_json(url, *, app_id, app_key, params=None, timeout=20):
    try:
        response = requests.get(url, headers=_headers(app_id, app_key), params=params, timeout=timeout)
    except requests.RequestException as exc:
        return {"ok": False, "status": "REQUEST_FAILED", "error": str(exc), "payload": None}
    if response.status_code != 200:
        return {
            "ok": False,
            "status": "HTTP_ERROR",
            "http_status": response.status_code,
            "error": "Tradera API returnerade fel.",
            "payload": None,
        }
    try:
        payload = response.json()
    except ValueError:
        return {"ok": False, "status": "INVALID_JSON", "error": "Ogiltigt JSON-svar från Tradera API.", "payload": None}
    return {"ok": True, "status": "OK", "payload": payload}


def resolve_seller_by_alias(alias, *, app_id, app_key, timeout=20):
    alias = str(alias or "").strip()
    if not alias:
        return {"ok": False, "status": "NO_ALIAS", "seller": None}
    result = _request_json(
        f"{BASE_URL}/users/by-alias/{quote(alias, safe='')}",
        app_id=app_id,
        app_key=app_key,
        timeout=timeout,
    )
    if not result.get("ok"):
        return {**result, "seller": None}
    payload = result.get("payload")
    if not isinstance(payload, dict):
        return {"ok": False, "status": "UNEXPECTED_USER_PAYLOAD", "seller": None}
    user_id = _pick(payload, "id", "Id", "userId", "UserId")
    resolved_alias = _pick(payload, "alias", "Alias", "username", "Username") or alias
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return {"ok": False, "status": "NO_USER_ID", "seller": None}
    return {
        "ok": True,
        "status": "OK",
        "seller": {"id": user_id, "alias": str(resolved_alias).strip()},
    }


def _shipping_cost(row):
    options = _pick(row, "shippingOptions", "ShippingOptions")
    costs = []
    if isinstance(options, list):
        for option in options:
            if not isinstance(option, dict):
                continue
            value = _pick(option, "cost", "Cost")
            number = _num(value)
            if number is not None and number >= 0:
                costs.append(number)
    return min(costs) if costs else None


def normalize_seller_item(row, *, seller_alias=None, seller_id=None):
    if not isinstance(row, dict):
        return None
    item_id = _pick(row, "id", "Id", "itemId", "ItemId")
    title = _pick(row, "shortDescription", "ShortDescription", "title", "Title")
    if item_id is None or not str(title or "").strip():
        return None

    buy_now = _num(_pick(row, "buyItNowPrice", "BuyItNowPrice"))
    next_bid = _num(_pick(row, "nextBid", "NextBid"))
    opening_bid = _num(_pick(row, "openingBid", "OpeningBid"))
    # For active auction inventory, next bid is the truthful current buy-in proxy.
    # For fixed price / explicit BIN, prefer buy-it-now.
    price = buy_now if buy_now is not None and buy_now > 0 else next_bid
    if price is None or price <= 0:
        price = opening_bid

    seller_obj = _pick(row, "seller", "Seller")
    alias = seller_alias
    sid = seller_id
    if isinstance(seller_obj, dict):
        alias = _pick(seller_obj, "alias", "Alias", "username", "Username") or alias
        sid = _pick(seller_obj, "id", "Id", "userId", "UserId") or sid

    url = _pick(row, "itemLink", "ItemLink", "itemUrl", "ItemUrl", "url", "Url")
    if not url:
        url = f"https://www.tradera.com/item/{item_id}"

    return {
        "titel": str(title).strip(),
        "pris": price,
        "frakt": _shipping_cost(row),
        "lank": str(url).strip(),
        "saljare": str(alias).strip() if alias else None,
        "seller_user_id": int(sid) if str(sid or "").isdigit() else sid,
        "slutdatum": _pick(row, "endDate", "EndDate"),
        "tradera_item_id": str(item_id),
        "source_type": "tradera_api_seller_inventory",
        "seller_inventory_candidate": True,
        "raw_api_item": row,
    }


def fetch_active_seller_items(*, seller_id, seller_alias=None, app_id, app_key, category_id=0, timeout=20):
    try:
        seller_id = int(seller_id)
    except (TypeError, ValueError):
        return {"ok": False, "status": "INVALID_SELLER_ID", "items": []}

    # ActiveFilter: 1 = active listings. This is read-only discovery.
    result = _request_json(
        f"{BASE_URL}/items/seller/{seller_id}",
        app_id=app_id,
        app_key=app_key,
        params={"categoryId": int(category_id or 0), "filterActive": 1},
        timeout=timeout,
    )
    if not result.get("ok"):
        return {**result, "items": []}
    payload = result.get("payload")
    if not isinstance(payload, list):
        return {"ok": False, "status": "UNEXPECTED_ITEMS_PAYLOAD", "items": []}
    items = []
    for row in payload:
        item = normalize_seller_item(row, seller_alias=seller_alias, seller_id=seller_id)
        if item:
            items.append(item)
    dedup = {}
    for item in items:
        key = item.get("tradera_item_id") or item.get("lank")
        if key:
            dedup[str(key)] = item
    return {
        "ok": True,
        "status": "OK",
        "items": list(dedup.values()),
        "raw_count": len(payload),
        "parsed_count": len(dedup),
    }


def discover_active_seller_inventory(*, seller_alias, app_id, app_key, category_id=0, timeout=20):
    resolved = resolve_seller_by_alias(seller_alias, app_id=app_id, app_key=app_key, timeout=timeout)
    if not resolved.get("ok"):
        return {"ok": False, "status": resolved.get("status"), "error": resolved.get("error"), "items": [], "seller": None}
    seller = resolved["seller"]
    fetched = fetch_active_seller_items(
        seller_id=seller["id"],
        seller_alias=seller.get("alias") or seller_alias,
        app_id=app_id,
        app_key=app_key,
        category_id=category_id,
        timeout=timeout,
    )
    return {**fetched, "seller": seller}
