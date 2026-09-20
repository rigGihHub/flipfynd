from __future__ import annotations

import re
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
    url = base + ("&" if "?" in base else "?") + f"page={page}"
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
        raise HTTPException(status_code=502, detail=f"tradera_http_{response.status_code}")

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
            "has_item_path": "/item/" in html,
            "html_prefix": re.sub(r"\\s+", " ", html[:180]),
        })

    item_ids = [str(x.get("tradera_item_id") or "") for x in items if x.get("tradera_item_id")]
    print(
        f"SELLER_PAGE seller={seller_id} requested_page={page} "
        f"count={len(items)} first_id={item_ids[0] if item_ids else '-'} "
        f"last_id={item_ids[-1] if item_ids else '-'} source_url={response.url}",
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
