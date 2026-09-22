"""Read public Tradera seller profile inventory without API credentials.

Seller Top 5 calls this helper with max_pages=1 so each click stays bounded.
The helper itself remains multi-page capable, detects repeated pages, and uses a
small embedded-JSON fallback only when no visible listing anchors exist.
"""
from __future__ import annotations

import html as _html
import json
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

_PROFILE_RE = re.compile(r"/profile/items/(?P<seller_id>\d+)(?:/(?P<alias>[^/?#]+))?/?(?:[?#]|$)", re.I)
_ITEM_HREF_RE = re.compile(r"href=[\"\'](?P<href>[^\"\']*/item/(?P<category>\d+)/(?P<id>\d+)[^\"\']*)[\"\']", re.I)
_ANCHOR_RE = re.compile(
    r"<a\b[^>]*\bhref=[\"'](?:https?://(?:www\.)?tradera\.com)?(?P<href>/item/(?P<category>\d+)/(?P<id>\d+)(?:/[^\"'<>\s?]*)?)[\"'][^>]*>(?P<body>.*?)</a>",
    re.I | re.S,
)
_PRICE_RE = re.compile(r"(?P<price>\d[\d\s.]*)\s*kr", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.I | re.S)
_PAGING_HINT_RE = re.compile(r"paging=(?:%3A|:)?(?P<page>\d+)(?:\.a0\.s|%2Ea0%2Es)(?P<count>\d+)", re.I)
_TOTAL_LISTINGS_RE = re.compile(r"(?P<count>\d[\d\s\u00a0.]*)\s+Annonser", re.I)
_PAGING_SUFFIX_CACHE: dict[str, str] = {}


def parse_profile_url(url: str | None) -> dict | None:
    text = str(url or "").strip()
    match = _PROFILE_RE.search(text)
    if not match:
        return None
    alias = str(match.group("alias") or "").strip() or None
    return {"seller_id": match.group("seller_id"), "alias": alias}


def build_profile_page_url(profile_url: str, page_number: int, paging_size: int | None = None) -> str:
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
        suffix = _PAGING_SUFFIX_CACHE.get(seller_id, "")
    if not suffix and paging_size:
        suffix = f".a0.s{int(paging_size)}"
    if not suffix:
        # This is only a bootstrap fallback. Once page 1 has been read, Tradera's
        # own paging link or the stored total listing estimate must be reused.
        suffix = ".a0.s48"
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
    if item_id is None or not str(item_id).isdigit() or not str(title or "").strip():
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
    }


def _extract_anchor_items(source: str, *, seller_alias=None, seller_id=None) -> dict[str, dict]:
    """Extract visible Tradera listing links tolerantly.

    Do not depend on one exact <a> serialization. Tradera has changed attribute
    order/query strings several times, which previously made a perfectly valid
    seller page look empty to FlipFynd.
    """
    dedup: dict[str, dict] = {}
    for match in _ITEM_HREF_RE.finditer(source):
        item_id = match.group("id")
        href = _html.unescape(match.group("href") or "")
        if href.startswith("http"):
            absolute_href = href
        else:
            slash = href.find("/item/")
            if slash < 0:
                continue
            absolute_href = "https://www.tradera.com" + href[slash:]

        # Prefer visible anchor text. Limit the search window so embedded JSON
        # cannot be mistaken for a gigantic title.
        a_start = source.rfind("<a", max(0, match.start() - 1200), match.start() + 1)
        if a_start < 0:
            a_start = match.start()
        open_end = source.find(">", match.end())
        close_end = source.find("</a>", max(match.end(), open_end))
        title = ""
        if open_end >= 0 and close_end >= 0 and close_end - open_end < 2500:
            title = _text(source[open_end + 1:close_end])

        # If the anchor is image-only, the human-readable slug is still better
        # than dropping the listing entirely. Embedded JSON remains a separate
        # fallback below and can later replace this with a richer title.
        if not title or len(title) > 350:
            path = absolute_href.split("?", 1)[0].rstrip("/")
            slug = path.rsplit("/", 1)[-1] if "/" in path else ""
            if slug and not slug.isdigit():
                title = _html.unescape(slug.replace("-", " ")).strip()
        if not title:
            title = f"Tradera-annons {item_id}"

        nearby_start = max(0, a_start - 300)
        nearby_end = min(len(source), (close_end + 700) if close_end >= 0 else match.end() + 1200)
        price = _num(_text(source[nearby_start:nearby_end]))
        dedup[item_id] = {
            "titel": title,
            "pris": price,
            "frakt": None,
            "lank": absolute_href,
            "saljare": seller_alias,
            "seller_user_id": seller_id,
            "tradera_item_id": item_id,
            "source_type": "tradera_public_seller_profile",
            "seller_inventory_candidate": True,
        }
    return dedup


def extract_public_profile_items(page_html: str, *, seller_alias=None, seller_id=None) -> list[dict]:
    source = str(page_html or "")
    anchors = _extract_anchor_items(source, seller_alias=seller_alias, seller_id=seller_id)
    if anchors:
        return list(anchors.values())

    dedup: dict[str, dict] = {}
    for script_body in _SCRIPT_RE.findall(source):
        body = _html.unescape(script_body.strip())
        if not body or body[0] not in "[{":
            continue
        try:
            payload = json.loads(body)
        except Exception:
            continue
        for obj in _walk_json(payload):
            item = _normalize_json_listing(obj, seller_alias=seller_alias, seller_id=seller_id)
            if item:
                dedup[item["tradera_item_id"]] = item
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
    max_pages: int = 1,
    timeout: int = 8,
    session=None,
    progress_callback=None,
    fallback_alias: str | None = None,
    paging_size: int | None = None,
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
    total_listing_estimate = None

    _emit_progress(progress_callback, phase="starting", page=page, pages_read=0, max_pages=max_pages, found_count=0, seller_alias=effective_alias)

    for _ in range(max_pages):
        url = build_profile_page_url(profile_url, page, paging_size=paging_size)
        _emit_progress(progress_callback, phase="fetching", page=page, pages_read=len(page_reports), max_pages=max_pages, found_count=len(all_items), seller_alias=effective_alias)
        try:
            response = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }, timeout=timeout)
        except requests.RequestException as exc:
            return {"ok": False, "status": "REQUEST_FAILED", "error": str(exc), "items": list(all_items.values()), "next_page": page, "page_reports": page_reports}
        if response.status_code != 200:
            return {"ok": False, "status": "HTTP_ERROR", "http_status": response.status_code, "items": list(all_items.values()), "next_page": page, "page_reports": page_reports}

        response_url = str(getattr(response, "url", None) or url)
        redirected_profile = parse_profile_url(response_url) or {}
        redirected_alias = str(redirected_profile.get("alias") or "").strip() or None
        if redirected_alias:
            effective_alias = redirected_alias
            parsed["alias"] = redirected_alias
        _remember_paging_suffix(response_url, response.text)

        total_match = _TOTAL_LISTINGS_RE.search(_text(response.text))
        if total_match:
            try:
                total_listing_estimate = int(re.sub(r"[^0-9]", "", total_match.group("count")))
            except (TypeError, ValueError):
                pass

        items = extract_public_profile_items(response.text, seller_alias=effective_alias, seller_id=parsed["seller_id"])
        ids = tuple(sorted(x["tradera_item_id"] for x in items if x.get("tradera_item_id")))
        page_reports.append({"page": page, "count": len(items), "url": response_url})

        if not items:
            return {
                "ok": False,
                "status": "NO_LISTINGS_IN_HTML",
                "error": "Tradera-sidan svarade men inga annonslänkar kunde läsas ur HTML-svaret.",
                "items": list(all_items.values()),
                "next_page": page,
                "pages_read": len(page_reports),
                "page_reports": page_reports,
                "total_listing_estimate": total_listing_estimate,
            }
        if previous_ids is not None and ids == previous_ids:
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
        "total_listing_estimate": total_listing_estimate,
    }


def crawl_public_seller_inventory(
    profile_url: str,
    *,
    start_page: int = 1,
    max_pages: int = 120,
    timeout: int = 8,
    progress_callback=None,
    fallback_alias: str | None = None,
    paging_size: int | None = None,
) -> dict:
    """Headless multi-page crawl for the background worker.

    Unlike the Streamlit controller this function owns the crawl loop itself,
    so it can keep advancing without browser reruns or button clicks.
    """
    all_items: dict[str, dict] = {}
    page = max(1, int(start_page or 1))
    total_pages = max(1, int(max_pages or 120))
    total_estimate = paging_size
    pages_read = 0
    last_result = None

    for _ in range(total_pages):
        result = fetch_public_seller_inventory_batch(
            profile_url,
            start_page=page,
            max_pages=1,
            timeout=timeout,
            progress_callback=progress_callback,
            fallback_alias=fallback_alias,
            paging_size=total_estimate,
        )
        last_result = result
        if not result.get("ok"):
            # An empty page after at least one successful page is normal EOF.
            if result.get("status") == "NO_LISTINGS_IN_HTML" and all_items:
                return {
                    "ok": True, "status": "OK", "items": list(all_items.values()),
                    "pages_read": pages_read, "next_page": page, "exhausted": True,
                    "total_listing_estimate": total_estimate,
                    "inventory_source": "TRADERA_PUBLIC_PROFILE",
                }
            out = dict(result)
            out["items"] = list(all_items.values())
            out["pages_read"] = pages_read
            out["next_page"] = page
            return out

        for item in result.get("items") or []:
            item_id = str(item.get("tradera_item_id") or "")
            if item_id:
                all_items[item_id] = item
        pages_read += int(result.get("pages_read") or 1)
        if result.get("total_listing_estimate"):
            total_estimate = int(result["total_listing_estimate"])
        page = int(result.get("next_page") or (page + 1))
        if result.get("exhausted"):
            break

    return {
        "ok": True, "status": "OK", "items": list(all_items.values()),
        "pages_read": pages_read, "next_page": page,
        "exhausted": bool((last_result or {}).get("exhausted")),
        "total_listing_estimate": total_estimate,
        "inventory_source": "TRADERA_PUBLIC_PROFILE",
    }
