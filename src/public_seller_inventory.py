"""Read public Tradera seller profile inventory without requiring API credentials.

This is discovery-only. It reads public profile pages in bounded batches, extracts
listing identity/title/explicit price when present, and never infers SOLD status,
market value or a buy decision.
"""
from __future__ import annotations

import html as _html
import json
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

_ITEM_HREF_RE = re.compile(r"/item/(?P<category>\d+)/(?P<id>\d+)(?:/[^\"'<>\s?]*)?", re.I)
_PROFILE_RE = re.compile(r"/profile/items/(?P<seller_id>\d+)/(?P<alias>[^/?#]+)", re.I)
_PRICE_RE = re.compile(r"(?P<price>\d[\d\s.]*)\s*kr", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.I | re.S)


def parse_profile_url(url: str | None) -> dict | None:
    text = str(url or "").strip()
    match = _PROFILE_RE.search(text)
    if not match:
        return None
    return {"seller_id": match.group("seller_id"), "alias": match.group("alias")}


def build_profile_page_url(profile_url: str, page_number: int) -> str:
    parsed = urlparse(str(profile_url or "").strip())
    query = parse_qs(parsed.query, keep_blank_values=True)
    # Tradera profile pagination currently accepts the opaque paging token with
    # the page number as its first component. Preserve any suffix when present.
    old = (query.get("paging") or [""])[0]
    suffix = ""
    if "." in old:
        suffix = old[old.find("."):]
    query["paging"] = [f"{max(1, int(page_number))}{suffix or '.a0.s7726'}"]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _text(value) -> str:
    value = _TAG_RE.sub(" ", str(value or ""))
    value = _html.unescape(value)
    return " ".join(value.split()).strip()


def _num(value):
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    match = _PRICE_RE.search(str(value or ""))
    if not match:
        return None
    try:
        return float(match.group("price").replace(" ", "").replace(".", ""))
    except ValueError:
        return None


def _pick(d, *keys):
    if not isinstance(d, dict):
        return None
    for key in keys:
        if d.get(key) not in (None, ""):
            return d.get(key)
    return None


def _walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _normalize_json_listing(row: dict, *, seller_alias=None, seller_id=None):
    item_id = _pick(row, "itemId", "ItemId", "id", "Id")
    title = _pick(row, "title", "Title", "shortDescription", "ShortDescription", "name", "Name")
    if item_id is None or not str(title or "").strip():
        return None
    # Reject generic/non-listing objects that happen to contain an id+name.
    if not str(item_id).isdigit():
        return None
    category = _pick(row, "categoryId", "CategoryId", "category", "Category")
    href = _pick(row, "itemLink", "ItemLink", "itemUrl", "ItemUrl", "url", "Url", "href")
    if href and "/item/" not in str(href):
        href = None
    price = _num(_pick(row, "buyItNowPrice", "BuyItNowPrice", "price", "Price", "nextBid", "NextBid", "currentBid", "CurrentBid"))
    if href is None and category is not None and str(category).isdigit():
        href = f"https://www.tradera.com/item/{category}/{item_id}"
    if href and str(href).startswith("/"):
        href = "https://www.tradera.com" + str(href)
    return {
        "titel": _text(title),
        "pris": price,
        "frakt": None,
        "lank": str(href).strip() if href else None,
        "saljare": seller_alias,
        "seller_user_id": seller_id,
        "tradera_item_id": str(item_id),
        "source_type": "tradera_public_seller_profile",
        "seller_inventory_candidate": True,
        "raw_public_item": row,
    }


def extract_public_profile_items(page_html: str, *, seller_alias=None, seller_id=None) -> list[dict]:
    """Extract public listings from embedded JSON first, then HTML anchors."""
    source = str(page_html or "")
    dedup: dict[str, dict] = {}

    for script_body in _SCRIPT_RE.findall(source):
        body = script_body.strip()
        if not body or body[0] not in "[{":
            continue
        try:
            payload = json.loads(_html.unescape(body))
        except Exception:
            continue
        for obj in _walk_json(payload):
            item = _normalize_json_listing(obj, seller_alias=seller_alias, seller_id=seller_id)
            if item:
                dedup[item["tradera_item_id"]] = item

    # Fallback for server-rendered profile cards. Capture the anchor text as
    # title and an explicit nearby SEK price; price may remain None if absent.
    for match in _ITEM_HREF_RE.finditer(source):
        item_id = match.group("id")
        if item_id in dedup:
            continue
        start = max(0, source.rfind("<a", 0, match.start()))
        end = source.find("</a>", match.end())
        if end < 0:
            end = min(len(source), match.end() + 800)
        else:
            end += 4
        anchor = source[start:end]
        title = _text(anchor)
        if not title:
            continue
        nearby = source[max(0, start - 500):min(len(source), end + 900)]
        price = _num(_text(nearby))
        href = match.group(0)
        dedup[item_id] = {
            "titel": title,
            "pris": price,
            "frakt": None,
            "lank": "https://www.tradera.com" + href,
            "saljare": seller_alias,
            "seller_user_id": seller_id,
            "tradera_item_id": item_id,
            "source_type": "tradera_public_seller_profile",
            "seller_inventory_candidate": True,
        }
    return list(dedup.values())


def fetch_public_seller_inventory_batch(
    profile_url: str,
    *,
    start_page: int = 1,
    max_pages: int = 12,
    timeout: int = 15,
    session=None,
) -> dict:
    parsed = parse_profile_url(profile_url)
    if not parsed:
        return {"ok": False, "status": "INVALID_PROFILE_URL", "items": [], "next_page": start_page}
    client = session or requests
    all_items: dict[str, dict] = {}
    page_reports = []
    exhausted = False
    previous_ids = None
    page = max(1, int(start_page or 1))
    for _ in range(max(1, int(max_pages or 1))):
        url = build_profile_page_url(profile_url, page)
        try:
            response = client.get(url, headers={"User-Agent": "Mozilla/5.0 FlipFynd/1.0", "Accept": "text/html"}, timeout=timeout)
        except requests.RequestException as exc:
            return {"ok": False, "status": "REQUEST_FAILED", "error": str(exc), "items": list(all_items.values()), "next_page": page, "page_reports": page_reports}
        if response.status_code != 200:
            return {"ok": False, "status": "HTTP_ERROR", "http_status": response.status_code, "items": list(all_items.values()), "next_page": page, "page_reports": page_reports}
        items = extract_public_profile_items(response.text, seller_alias=parsed["alias"], seller_id=parsed["seller_id"])
        ids = tuple(sorted(x["tradera_item_id"] for x in items if x.get("tradera_item_id")))
        page_reports.append({"page": page, "count": len(items), "url": url})
        if not items or ids == previous_ids:
            exhausted = True
            break
        previous_ids = ids
        for item in items:
            all_items[item["tradera_item_id"]] = item
        page += 1
    return {
        "ok": True,
        "status": "OK",
        "seller": parsed,
        "items": list(all_items.values()),
        "parsed_count": len(all_items),
        "pages_read": len(page_reports),
        "page_reports": page_reports,
        "next_page": page,
        "exhausted": exhausted,
        "inventory_source": "TRADERA_PUBLIC_PROFILE",
    }
