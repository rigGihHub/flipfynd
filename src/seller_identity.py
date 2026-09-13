"""Recover seller identity across fetched, analysed and API-backed listing shapes."""
from __future__ import annotations


def seller_alias(item: dict | None) -> str | None:
    item = item or {}
    for key in (
        "saljare", "säljare", "seller", "seller_name", "username",
        "seller_detail", "seller_alias", "alias",
    ):
        value = item.get(key)
        if isinstance(value, dict):
            for nested_key in ("alias", "Alias", "username", "Username", "name", "Name"):
                nested = value.get(nested_key)
                if nested not in (None, "") and str(nested).strip():
                    return str(nested).strip()
        elif value not in (None, "") and str(value).strip():
            return str(value).strip()

    for container_key in ("raw_api_item", "raw_item", "source_item"):
        nested = item.get(container_key)
        if isinstance(nested, dict):
            seller = seller_alias(nested)
            if seller:
                return seller
    return None


def _tokens(item: dict | None):
    item = item or {}
    ids = {
        str(item.get(key)).strip()
        for key in ("tradera_item_id", "item_id", "id")
        if item.get(key) not in (None, "")
    }
    urls = {
        str(item.get(key)).strip()
        for key in ("lank", "url", "link", "href", "item_url", "tradera_url")
        if item.get(key)
    }
    title = str(item.get("titel") or item.get("title") or "").strip().casefold()
    return ids, urls, title


def recover_seller_from_market(item: dict | None, market_items) -> tuple[str | None, dict]:
    """Recover a seller from the original loaded listing without inventing identity.

    Strong item id / URL matches win. Title+price is only a fallback when both match.
    """
    item = dict(item or {})
    direct = seller_alias(item)
    if direct:
        return direct, item

    ids, urls, title = _tokens(item)
    for source in market_items or []:
        if not isinstance(source, dict):
            continue
        s_ids, s_urls, s_title = _tokens(source)
        same = bool(ids & s_ids or urls & s_urls)
        if not same and title and s_title == title:
            try:
                p1 = float(item.get("pris") or item.get("price"))
                p2 = float(source.get("pris") or source.get("price"))
                same = abs(p1 - p2) < 0.01
            except (TypeError, ValueError):
                same = False
        if not same:
            continue
        recovered = seller_alias(source)
        if recovered:
            merged = dict(source)
            merged.update(item)
            return recovered, merged
    return None, item
