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


def _price_key(item: dict | None):
    item = item or {}
    try:
        value = item.get("pris")
        if value in (None, ""):
            value = item.get("price")
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _same_listing(left: dict, right: dict) -> bool:
    left_ids, left_urls, left_title = _tokens(left)
    right_ids, right_urls, right_title = _tokens(right)
    if left_ids & right_ids or left_urls & right_urls:
        return True
    if not left_title or left_title != right_title:
        return False
    p1 = _price_key(left)
    p2 = _price_key(right)
    return p1 is not None and p2 is not None and abs(p1 - p2) < 0.01


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


def _seller_signature(item: dict) -> tuple[str, str, str]:
    return (
        (seller_alias(item) or "").casefold(),
        seller_id(item) or "",
        seller_url(item) or "",
    )


def _add_unique(index: dict, key, donor: dict):
    """Index a donor only while all donors for the key agree on seller identity."""
    if key in (None, ""):
        return
    existing = index.get(key)
    if existing is None and key not in index:
        index[key] = donor
        return
    if existing is None:
        return
    if _seller_signature(existing) != _seller_signature(donor):
        index[key] = None


def backfill_seller_metadata(items) -> list[dict]:
    """Retroactively copy seller metadata between safely matched listing copies.

    This is intentionally indexed rather than pairwise. Strong item-id/URL keys
    are preferred; title+price is only used when that fallback key maps to one
    unambiguous seller identity. Existing non-empty values are never overwritten.
    The indexed design keeps large seller inventories practical instead of O(n²).
    """
    rows = [apply_seller_metadata(x) for x in (items or []) if isinstance(x, dict)]
    donors = [row for row in rows if seller_alias(row) or seller_id(row) or seller_url(row)]

    by_id = {}
    by_url = {}
    by_title_price = {}
    for donor in donors:
        ids, urls, title = _tokens(donor)
        for value in ids:
            _add_unique(by_id, value, donor)
        for value in urls:
            _add_unique(by_url, value, donor)
        price = _price_key(donor)
        if title and price is not None:
            _add_unique(by_title_price, (title, price), donor)

    result = []
    for row in rows:
        ids, urls, title = _tokens(row)
        strong = []
        for value in ids:
            donor = by_id.get(value)
            if donor is not None:
                strong.append(donor)
        for value in urls:
            donor = by_url.get(value)
            if donor is not None:
                strong.append(donor)

        enriched = row
        if strong:
            # Multiple strong keys may point to the same seller; apply all
            # agreeing metadata without overwriting fields already present.
            signatures = {_seller_signature(donor) for donor in strong}
            if len(signatures) == 1:
                for donor in strong:
                    if donor is not row:
                        enriched = apply_seller_metadata(enriched, donor)
        else:
            price = _price_key(row)
            donor = by_title_price.get((title, price)) if title and price is not None else None
            if donor is not None and donor is not row:
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
