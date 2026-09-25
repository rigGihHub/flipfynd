from __future__ import annotations

import re
import html as html_lib
from urllib.parse import urljoin, urlparse
from fastapi import FastAPI, HTTPException, Query
from curl_cffi import requests as curl_requests

from src.public_seller_inventory import extract_public_profile_items

def _decode_embedded_markup(value: str) -> str:
    value = html_lib.unescape(value or "")
    for _ in range(2):
        value = (value.replace("\\u003c", "<").replace("\\u003e", ">")
                 .replace("\\u0026", "&").replace("\\u0022", '"')
                 .replace("\\u0027", "'").replace("\\\"", '"'))
    return value


def _page_href(markup: str, page: int) -> str | None:
    text = _decode_embedded_markup(markup)
    # Tradera's observed production markup:
    # aria-label="Sida 2" href="/profile/items/...?...paging=2.a0.s9529"
    patterns = (
        rf'aria-label=["\']Sida {page}["\'][^>]*href=["\']([^"\']+)["\']',
        rf'href=["\']([^"\']*paging={page}\.a0\.s\d+[^"\']*)["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return html_lib.unescape(match.group(1))
    return None


app = FastAPI(title="FlipFynd Seller Fetch Proxy")
# In-process cursor cache: once Tradera exposes the real next-page URL, later
# requests can jump straight to it instead of replaying pages 1..N. This cache
# is an acceleration only; correctness still falls back to walking from page 1.
_PAGE_URL_CACHE: dict[tuple[str, str, int], str] = {}


def _cache_key(seller_id: int, alias: str, page: int) -> tuple[str, str, int]:
    return (str(seller_id), str(alias or "").strip().casefold(), int(page))


def _safe_tradera_page_url(value: str) -> bool:
    try:
        parsed = urlparse(str(value or ""))
        return parsed.scheme == "https" and parsed.netloc.lower().endswith("tradera.com") and "/profile/items/" in parsed.path
    except Exception:
        return False
_TOTAL_RE = re.compile(r"(?P<count>\d[\d\s\u00a0.]*)\s+Annonser", re.I)
_TRADERA_PAGE_SIZE = 80


def _total_listing_count(markup: str) -> int | None:
    match = _TOTAL_RE.search(markup or "")
    if not match:
        return None
    try:
        return int(re.sub(r"[^0-9]", "", match.group("count")))
    except (TypeError, ValueError):
        return None


def _is_exhausted_page(markup: str, page: int, item_count: int) -> bool:
    """Use both inventory count and page shape to distinguish EOF from errors."""
    if _page_href(markup, int(page) + 1):
        return False
    total = _total_listing_count(markup)
    represented_capacity = max(1, int(page)) * _TRADERA_PAGE_SIZE
    return bool(
        item_count > 0
        and (
            item_count < _TRADERA_PAGE_SIZE
            or (total is not None and represented_capacity >= total)
        )
    )


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/seller/{seller_id}")
def seller_page(
    seller_id: int,
    page: int = Query(1, ge=1, le=10000),
    alias: str | None = None,
):
    alias_clean = (alias or "").strip()
    base = f"https://www.tradera.com/profile/items/{seller_id}/"
    if alias_clean:
        base += alias_clean
    # Tradera's current seller profile does not honor the old paging token
    # reliably. Use its ordinary page query first; the response URL and item
    # fingerprints below verify whether the requested page was actually served.
    # The HTML exposes Tradera's real paging contract, e.g.
    # paging=2.a0.s9529 where s is the seller inventory size (not page size).
    # For this endpoint we can derive that total from page 1 on each request
    # and then request the desired page using the same contract.
    if page <= 1:
        url = base
    else:
        cached_url = _PAGE_URL_CACHE.get(_cache_key(seller_id, alias_clean, page))
        if cached_url and _safe_tradera_page_url(cached_url):
            url = cached_url
            print(f"SELLER_PAGE_CACHE_HIT seller={seller_id} page={page} url={url}", flush=True)
        else:
            # Walk only until the requested page when no trustworthy cursor is
            # cached. Each discovered page URL is cached, so a sequential crawl
            # pays this cost once and page N+1 becomes a direct request.
            seed_url = base
            seed = None
            for target_page in range(2, page + 1):
                known = _PAGE_URL_CACHE.get(_cache_key(seller_id, alias_clean, target_page))
                if known and _safe_tradera_page_url(known):
                    seed_url = known
                    continue
                seed = curl_requests.get(
                    seed_url, impersonate="chrome", timeout=15,
                    headers={"Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8", "Cache-Control": "no-cache"},
                )
                next_href = _page_href(seed.text or "", target_page)
                if not next_href:
                    seed_items = extract_public_profile_items(
                        seed.text or "", seller_alias=alias_clean or None,
                        seller_id=str(seller_id),
                    )
                    seed_page = max(1, target_page - 1)
                    if seed.status_code == 200 and _is_exhausted_page(
                        seed.text or "", seed_page, len(seed_items)
                    ):
                        total = _total_listing_count(seed.text or "")
                        print(
                            f"SELLER_END seller={seller_id} requested_page={page} "
                            f"last_page={seed_page} last_count={len(seed_items)} total={total}",
                            flush=True,
                        )
                        return {
                            "ok": True,
                            "seller_id": str(seller_id),
                            "alias": alias_clean or None,
                            "page": page,
                            "next_page": page,
                            "items": [],
                            "parsed_count": 0,
                            "total_listing_estimate": total,
                            "exhausted": True,
                            "end_reason": "NO_NEXT_PAGE_AFTER_FINAL_PARTIAL_PAGE",
                            "source_url": str(seed.url),
                        }
                    detail = {
                        "code": "FF-SELLER-PAGE-LINK-NOT-FOUND",
                        "requested_page": page,
                        "missing_target_page": target_page,
                        "seed_status": seed.status_code,
                        "seed_url": str(seed.url),
                    }
                    print(f"SELLER_PAGING_ERROR {detail}", flush=True)
                    raise HTTPException(status_code=502, detail=detail)
                seed_url = urljoin(str(seed.url), next_href)
                if _safe_tradera_page_url(seed_url):
                    _PAGE_URL_CACHE[_cache_key(seller_id, alias_clean, target_page)] = seed_url
            url = seed_url
            print(f"SELLER_PAGE_CHAIN seller={seller_id} page={page} url={url}", flush=True)
    try:
        response = curl_requests.get(
            url,
            impersonate="chrome",
            timeout=15,
            headers={
                "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"tradera_fetch_failed: {exc}") from exc
    if response.status_code != 200:
        detail = {
            "code": "FF-SELLER-TRADERA-HTTP",
            "requested_page": page,
            "tradera_status": response.status_code,
            "requested_url": url,
            "response_url": str(response.url),
        }
        print(f"SELLER_PAGING_ERROR {detail}", flush=True)
        raise HTTPException(status_code=502, detail=detail)

    html = response.text or ""
    items = extract_public_profile_items(
        html,
        seller_alias=alias_clean or None,
        seller_id=str(seller_id),
    )
    total = _total_listing_count(html)

    if not items:
        raise HTTPException(status_code=502, detail={
            "code": "no_listings_parsed",
            "requested_page": page,
            "requested_url": url,
            "response_url": str(response.url),
            "html_length": len(html),
            "has_item_path": "/item/" in html,
            "html_prefix": re.sub(r"\\s+", " ", html[:180]),
        })

    # Cache the real next-page URL from the page just fetched. This turns the
    # normal sequential crawl into roughly one Tradera request per new page.
    next_href = _page_href(html, page + 1)
    next_url = urljoin(str(response.url), next_href) if next_href else None
    exhausted = _is_exhausted_page(html, page, len(items))
    if next_url and _safe_tradera_page_url(next_url):
        _PAGE_URL_CACHE[_cache_key(seller_id, alias_clean, page + 1)] = next_url

    item_ids = [str(x.get("tradera_item_id") or "") for x in items if x.get("tradera_item_id")]
    # Capture navigation/cursor evidence from the real HTML instead of
    # assuming a page-number contract.
    nav_links = []
    for match in re.finditer(r'href=["\\\']([^"\\\']+)["\\\']', html, re.I):
        href = match.group(1)
        if "paging=" in href or "page=" in href or "cursor" in href.lower():
            absolute = urljoin(str(response.url), href)
            if absolute not in nav_links:
                nav_links.append(absolute)
            if len(nav_links) >= 12:
                break
    print(
        f"SELLER_PAGE seller={seller_id} requested_page={page} "
        f"count={len(items)} first_id={item_ids[0] if item_ids else '-'} "
        f"last_id={item_ids[-1] if item_ids else '-'} source_url={response.url} "
        f"nav_links={nav_links[:4]}",
        flush=True,
    )

    return {
        "ok": True,
        "seller_id": str(seller_id),
        "alias": alias_clean or None,
        "page": page,
        "next_page": page + 1,
        "items": items,
        "parsed_count": len(items),
        "total_listing_estimate": total,
        "source_url": str(response.url),
        "requested_url": url,
        "html_length": len(html),
        "next_url": next_url,
        "cursor_cached": bool(next_url),
        "exhausted": exhausted,
        "end_reason": "NO_NEXT_PAGE_AFTER_FINAL_PARTIAL_PAGE" if exhausted else None,
    }
