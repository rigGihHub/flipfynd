from __future__ import annotations

import re
import html as html_lib
from urllib.parse import urljoin
from fastapi import FastAPI, HTTPException, Query
from curl_cffi import requests as curl_requests

from src.public_seller_inventory import extract_public_profile_items

app = FastAPI(title="FlipFynd Seller Fetch Proxy")
_TOTAL_RE = re.compile(r"(?P<count>\d[\d\s\u00a0.]*)\s+Annonser", re.I)


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
        seed = curl_requests.get(
            base, impersonate="chrome", timeout=15,
            headers={"Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8", "Cache-Control": "no-cache"},
        )
        seed_html = seed.text or ""
        decoded_seed = html_lib.unescape(seed_html).replace("\\u0026", "&")
        paging_match = re.search(r"paging=(?:%3A|:)?2\\.a0\\.s(?P<size>\\d+)", seed_html, re.I)
        if not paging_match:
            paging_match = re.search(r"paging=2\\.a0\\.s(?P<size>\\d+)", seed_html.replace("&amp;", "&"), re.I)
        if not paging_match:
            token_probe = re.search(r"[0-9]+[.]a0[.]s[0-9]+", decoded_seed, re.I)
            paging_pos = token_probe.start() if token_probe else decoded_seed.lower().find("paging=")
            paging_excerpt = (
                decoded_seed[max(0, paging_pos - 80): paging_pos + 220]
                if paging_pos >= 0 else ""
            )
            paging_excerpt = re.sub(r"\\s+", " ", paging_excerpt)
            detail = {
                "code": "FF-SELLER-PAGING-CONTRACT-NOT-FOUND",
                "requested_page": page,
                "seed_status": seed.status_code,
                "seed_url": str(seed.url),
                "seed_html_length": len(seed_html),
                "has_paging_literal": "paging=" in seed_html,
                "paging_excerpt": paging_excerpt,
            }
            print(f"SELLER_PAGING_ERROR {detail}", flush=True)
            raise HTTPException(status_code=502, detail=detail)
        paging_size = paging_match.group("size")
        url = base + ("&" if "?" in base else "?") + f"paging={page}.a0.s{paging_size}"
        print(
            f"SELLER_PAGING_CONTRACT seller={seller_id} page={page} "
            f"size={paging_size} url={url}",
            flush=True,
        )
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
    total = None
    match = _TOTAL_RE.search(html)
    if match:
        try:
            total = int(re.sub(r"[^0-9]", "", match.group("count")))
        except Exception:
            total = None

    if not items:
        raise HTTPException(status_code=502, detail={
            "code": "no_listings_parsed",
            "requested_page": page,
            "requested_url": url,
            "response_url": str(response.url),
            "html_length": len(html),
        "navigation_links": nav_links,
            "has_item_path": "/item/" in html,
            "html_prefix": re.sub(r"\\s+", " ", html[:180]),
        })

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
    }
