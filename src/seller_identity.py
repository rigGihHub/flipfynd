"""Recover seller identity across fetched, analysed and API-backed listing shapes."""
from __future__ import annotations


def _text(value) -> str:
    return str(value or "").strip()


def seller_alias(item: dict | None) -> str | None:
    item = item or {}
    for key in (
        "saljare", "säljare", "seller", "seller_name", "username",
        "seller_detail", "seller_alias", "saljare_alias", "alias",
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


def seller_id(item: dict | None) -> str | None:
    item = item or {}
    for key in ("seller_id", "saljare_id", "SellerId", "sellerId"):
        value = item.get(key)
        if value not in (None, "") and str(value).strip():
            return str(value).strip()
    for key in ("seller", "seller_detail"):
        value = item.get(key)
        if isinstance(value, dict):
            for nested_key in ("id", "Id", "ID", "SellerId", "seller_id"):
                nested = value.get(nested_key)
                if nested not in (None, "") and str(nested).strip():
                    return str(nested).strip()
    for container_key in ("raw_api_item", "raw_item", "source_item"):
        nested = item.get(container_key)
        if isinstance(nested, dict):
            value = seller_id(nested)
            if value:
                return value
    return None


def seller_url(item: dict | None) -> str | None:
    item = item or {}
    for key in ("seller_url", "saljare_url", "seller_profile_url", "seller_store_url"):
        value = item.get(key)
        if value not in (None, "") and str(value).strip():
            return str(value).strip()
    for key in ("seller", "seller_detail"):
        value = item.get(key)
        if isinstance(value, dict):
            for nested_key in ("url", "Url", "URL", "ProfileUrl", "profile_url", "StoreUrl", "store_url"):
                nested = value.get(nested_key)
                if nested not in (None, "") and str(nested).strip():
                    return str(nested).strip()
    for container_key in ("raw_api_item", "raw_item", "source_item"):
        nested = item.get(container_key)
        if isinstance(nested, dict):
            value = seller_url(nested)
            if value:
                return value
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


def _same_listing(left: dict, right: dict) -> bool:
    left_ids, left_urls, left_title = _tokens(left)
    right_ids, right_urls, right_title = _tokens(right)
    if left_ids & right_ids or left_urls & right_urls:
        return True
    if not left_title or left_title != right_title:
        return False
    try:
        p1 = float(left.get("pris") or left.get("price"))
        p2 = float(right.get("pris") or right.get("price"))
        return abs(p1 - p2) < 0.01
    except (TypeError, ValueError):
        return False


def apply_seller_metadata(item: dict | None, source: dict | None = None) -> dict:
    """Fill canonical seller metadata without overwriting non-empty listing fields."""
    out = dict(item or {})
    source = source or item or {}
    alias = seller_alias(source)
    sid = seller_id(source)
    surl = seller_url(source)

    if alias:
        for key in ("saljare_alias", "seller_alias", "seller_name"):
            if not _text(out.get(key)):
                out[key] = alias
    if sid:
        for key in ("saljare_id", "seller_id"):
            if not _text(out.get(key)):
                out[key] = sid
    if surl:
        for key in ("saljare_url", "seller_url"):
            if not _text(out.get(key)):
                out[key] = surl
    return out


def backfill_seller_metadata(items) -> list[dict]:
    """Retroactively copy seller metadata only between safely matched copies of a listing.

    Strong item-id or URL matches win. Title+price is only a fallback. Existing
    non-empty values are never overwritten.
    """
    rows = [apply_seller_metadata(x) for x in (items or []) if isinstance(x, dict)]
    donors = [row for row in rows if seller_alias(row) or seller_id(row) or seller_url(row)]
    result = []
    for row in rows:
        enriched = row
        for donor in donors:
            if donor is row or not _same_listing(row, donor):
                continue
            enriched = apply_seller_metadata(enriched, donor)
        result.append(enriched)
    return result


def recover_seller_from_market(item: dict | None, market_items) -> tuple[str | None, dict]:
    """Recover a seller from the original loaded listing without inventing identity.

    Strong item id / URL matches win. Title+price is only a fallback when both match.
    Seller alias/id/url are copied into canonical fields when available.
    """
    item = apply_seller_metadata(item)
    direct = seller_alias(item)
    if direct:
        return direct, item

    for source in market_items or []:
        if not isinstance(source, dict) or not _same_listing(item, source):
            continue
        recovered = seller_alias(source)
        if recovered:
            merged = dict(source)
            merged.update(item)
            merged = apply_seller_metadata(merged, source)
            return recovered, merged
    return None, item
