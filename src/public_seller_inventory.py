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
_PROFILE_RE = re.compile(r"/profile/items/(?P<seller_id>\d+)(?:/(?P<alias>[^/?#]+))?/?(?:[?#]|$)", re.I)
_PRICE_RE = re.compile(r"(?P<price>\d[\d\s.]*)\s*kr", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.I | re.S)
_PAGING_HINT_RE = re.compile(r"paging=\d+\.a0\.s(?P<count>\d+)", re.I)
_TOTAL_LISTINGS_RE = re.compile(r"(?P<count>\d[\d\s\u00a0.]*)\s+Annonser", re.I)
_PAGING_SUFFIX_CACHE: dict[str, str] = {}


def parse_profile_url(url: str | None) -> dict | None:
    text = str(url or "").strip()
    match = _PROFILE_RE.search(text)
    if not match:
        return None
    alias = str(match.group("alias") or "").strip() or None
    return {"seller_id": match.group("seller_id"), "alias": alias}


def build_profile_page_url(profile_url: str, page_number: int) -> str:
    parsed = urlparse(str(profile_url or "").strip())
    query = parse_qs(parsed.query, keep_blank_values=True)
    page_number = max(1, int(page_number))
    old = (query.get("paging") or [""])[0]
    # Important: page 1 must use the canonical profile URL if no paging token is
    # already present. A fabricated token can make Tradera return an empty page.
    if page_number == 1 and not old:
        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
    suffix = ""
    if "." in old:
        suffix = old[old.find("."):]
    if not suffix:
        profile = parse_profile_url(profile_url) or {}
        seller_id = str(profile.get("seller_id") or "")
        suffix = _PAGING_SUFFIX_CACHE.get(seller_id, ".a0.s48")
    query["paging"] = [f"{page_number}{suffix}"]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _remember_paging_suffix(profile_url: str, page_html: str) -> None:
    profile = parse_profile_url(profile_url) or {}
    seller_id = str(profile.get("seller_id") or "")
    if not seller_id:
        return
    match = _PAGING_HINT_RE.search(_html.unescape(str(page_html or "")))
    if match:
        _PAGING_SUFFIX_CACHE[seller_id] = f".a0.s{match.group('count')}"


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


def _extract_anchor_items(source: str, *, seller_alias=None, seller_id=None) -> dict[str, dict]:
    dedup: dict[str, dict] = {}
    for match in _ITEM_HREF_RE.finditer(source):
        item_id = match.group("id")
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
    return dedup


def extract_public_profile_items(page_html: str, *, seller_alias=None, seller_id=None) -> list[dict]:
    """Extract the seller's visible listing cards and use embedded JSON only as enrichment.

    Tradera pages can contain unrelated recommendation/search JSON. Treating every
    item-like JSON object as seller inventory polluted Seller Top 5 with thousands
    of unrelated rows. Visible /item/ anchors are the authoritative page inventory.
    """
    source = str(page_html or "")
    dedup = _extract_anchor_items(source, seller_alias=seller_alias, seller_id=seller_id)
    allow_new_json_items = not dedup
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
            if not item:
                continue
            item_id = item["tradera_item_id"]
            if item_id in dedup:
                current = dedup[item_id]
                if item.get("titel"):
                    current["titel"] = item["titel"]
                if item.get("pris") is not None:
                    current["pris"] = item["pris"]
                if item.get("lank"):
                    current["lank"] = item["lank"]
                current["raw_public_item"] = item.get("raw_public_item")
            elif allow_new_json_items:
                dedup[item_id] = item
    return list(dedup.values())


def _emit_progress(callback, **payload):
    if not callable(callback):
        return
    try:
        callback(dict(payload))
    except Exception:
        pass


def fetch_public_seller_inventory_batch(
    profile_url: str,
    *,
    start_page: int = 1,
    max_pages: int = 12,
    timeout: int = 15,
    session=None,
    progress_callback=None,
    fallback_alias: str | None = None,
) -> dict:
    parsed = parse_profile_url(profile_url)
    if not parsed:
        return {"ok": False, "status": "INVALID_PROFILE_URL", "items": [], "next_page": start_page}
    effective_alias = str(parsed.get("alias") or fallback_alias or "").strip() or None
    parsed = dict(parsed)
    parsed["alias"] = effective_alias
    client = session or requests
    all_items: dict[str, dict] = {}
    page_reports = []
    exhausted = False
    previous_ids = None
    page = max(1, int(start_page or 1))
    max_pages = max(1, int(max_pages or 1))
    _emit_progress(progress_callback, phase="starting", page=page, pages_read=0, max_pages=max_pages, found_count=0, seller_alias=effective_alias)
    for _ in range(max_pages):
        url = build_profile_page_url(profile_url, page)
        _emit_progress(progress_callback, phase="fetching", page=page, pages_read=len(page_reports), max_pages=max_pages, found_count=len(all_items), seller_alias=effective_alias)
        try:
            response = client.get(url, headers={"User-Agent": "Mozilla/5.0 FlipFynd/1.0", "Accept": "text/html"}, timeout=timeout)
        except requests.RequestException as exc:
            _emit_progress(progress_callback, phase="error", page=page, pages_read=len(page_reports), max_pages=max_pages, found_count=len(all_items), status="REQUEST_FAILED")
            return {"ok": False, "status": "REQUEST_FAILED", "error": str(exc), "items": list(all_items.values()), "next_page": page, "page_reports": page_reports}
        if response.status_code != 200:
            _emit_progress(progress_callback, phase="error", page=page, pages_read=len(page_reports), max_pages=max_pages, found_count=len(all_items), status="HTTP_ERROR")
            return {"ok": False, "status": "HTTP_ERROR", "http_status": response.status_code, "items": list(all_items.values()), "next_page": page, "page_reports": page_reports}
        response_url = str(getattr(response, "url", None) or url)
        redirected_profile = parse_profile_url(response_url) or {}
        redirected_alias = str(redirected_profile.get("alias") or "").strip() or None
        if redirected_alias:
            effective_alias = redirected_alias
            parsed["alias"] = redirected_alias
        _remember_paging_suffix(response_url, response.text)
        total_listing_estimate = None
        total_match = _TOTAL_LISTINGS_RE.search(_text(response.text))
        if total_match:
            try:
                total_listing_estimate = int(re.sub(r"[^0-9]", "", total_match.group("count")))
            except (TypeError, ValueError):
                total_listing_estimate = None
        items = extract_public_profile_items(response.text, seller_alias=effective_alias, seller_id=parsed["seller_id"])
        ids = tuple(sorted(x["tradera_item_id"] for x in items if x.get("tradera_item_id")))
        page_reports.append({"page": page, "count": len(items), "url": response_url})
        if not items or ids == previous_ids:
            exhausted = True
            _emit_progress(progress_callback, phase="exhausted", page=page, pages_read=len(page_reports), max_pages=max_pages, found_count=len(all_items), page_count=len(items), seller_alias=effective_alias)
            break
        previous_ids = ids
        for item in items:
            all_items[item["tradera_item_id"]] = item
        _emit_progress(progress_callback, phase="page_complete", page=page, pages_read=len(page_reports), max_pages=max_pages, found_count=len(all_items), page_count=len(items), seller_alias=effective_alias)
        page += 1
    _emit_progress(progress_callback, phase="complete", page=page, pages_read=len(page_reports), max_pages=max_pages, found_count=len(all_items), exhausted=exhausted, seller_alias=effective_alias)
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
        "total_listing_estimate": locals().get("total_listing_estimate"),
    }
