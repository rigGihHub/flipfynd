"""Read public Tradera seller profile inventory without requiring API credentials.

This is discovery-only. It reads one public profile page at a time, extracts
visible listing anchors quickly, and never infers SOLD status, market value or a
buy decision.
"""
from __future__ import annotations

import html as _html
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

_ITEM_HREF_RE = re.compile(r"/item/(?P<category>\d+)/(?P<id>\d+)(?:/[^\"'<>\s?]*)?", re.I)
_PROFILE_RE = re.compile(r"/profile/items/(?P<seller_id>\d+)(?:/(?P<alias>[^/?#]+))?/?(?:[?#]|$)", re.I)
_PRICE_RE = re.compile(r"(?P<price>\d[\d\s.]*)\s*kr", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
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


def _extract_anchor_items(source: str, *, seller_alias=None, seller_id=None) -> dict[str, dict]:
    """Fast path: visible Tradera listing anchors only.

    Do not recursively walk embedded JSON here. Some Tradera profile pages carry
    very large script payloads, and traversing them can keep a Streamlit request
    busy long enough to look frozen. Seller Top 5 only needs the visible page
    inventory for checkpointed discovery.
    """
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
        nearby = source[max(0, start - 400):min(len(source), end + 700)]
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
    return list(_extract_anchor_items(str(page_html or ""), seller_alias=seller_alias, seller_id=seller_id).values())


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
    max_pages: int = 1,
    timeout: int = 8,
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
    # Hard safety rule: exactly one Tradera profile page per user action.
    max_pages = 1
    _emit_progress(progress_callback, phase="starting", page=page, pages_read=0, max_pages=1, found_count=0, seller_alias=effective_alias)
    for _ in range(max_pages):
        url = build_profile_page_url(profile_url, page)
        _emit_progress(progress_callback, phase="fetching", page=page, pages_read=0, max_pages=1, found_count=0, seller_alias=effective_alias)
        try:
            response = client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 FlipFynd/1.0", "Accept": "text/html"},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            _emit_progress(progress_callback, phase="error", page=page, pages_read=0, max_pages=1, found_count=0, status="REQUEST_FAILED")
            return {"ok": False, "status": "REQUEST_FAILED", "error": str(exc), "items": [], "next_page": page, "page_reports": []}
        if response.status_code != 200:
            _emit_progress(progress_callback, phase="error", page=page, pages_read=0, max_pages=1, found_count=0, status="HTTP_ERROR")
            return {"ok": False, "status": "HTTP_ERROR", "http_status": response.status_code, "items": [], "next_page": page, "page_reports": []}

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
        else:
            previous_ids = ids
            for item in items:
                all_items[item["tradera_item_id"]] = item
            page += 1

        _emit_progress(
            progress_callback,
            phase="page_complete" if items else "exhausted",
            page=page - 1 if items else page,
            pages_read=1,
            max_pages=1,
            found_count=len(all_items),
            page_count=len(items),
            seller_alias=effective_alias,
        )

    _emit_progress(progress_callback, phase="complete", page=page, pages_read=1, max_pages=1, found_count=len(all_items), exhausted=exhausted, seller_alias=effective_alias)
    return {
        "ok": True,
        "status": "OK",
        "seller": parsed,
        "items": list(all_items.values()),
        "parsed_count": len(all_items),
        "pages_read": 1,
        "page_reports": page_reports,
        "next_page": page,
        "exhausted": exhausted,
        "inventory_source": "TRADERA_PUBLIC_PROFILE",
        "total_listing_estimate": total_listing_estimate,
    }
