"""Read acquisition costs from the exact public listing, never related ads."""
import json
import re
from html import unescape
from urllib.parse import urlsplit

import requests


def parse_purchase_detail(html, item_id):
    decoder = json.JSONDecoder()
    for script in re.findall(r'self\.__next_f\.push\((\[.*?\])\)</script>', html, re.S):
        try:
            payload = json.loads(script)
            text = payload[1] if len(payload) > 1 and isinstance(payload[1], str) else ""
        except (ValueError, TypeError):
            continue
        for match in re.finditer(r'"itemDetails"\s*:\s*(\{)', text):
            try:
                detail, _ = decoder.raw_decode(text, match.start(1))
            except ValueError:
                continue
            if str(detail.get("itemId")) == str(item_id):
                return detail
    return {}


def verify_purchase_cost(item, *, session=requests):
    out = dict(item)
    url = str(item.get("lank") or item.get("url") or "")
    parts = urlsplit(url)
    match = re.match(r"/item/\d+/(\d+)(?:/|$)", parts.path)
    if parts.scheme != "https" or parts.hostname not in {"www.tradera.com", "tradera.com"} or not match:
        return out
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        detail = parse_purchase_detail(response.text, match[1])
        if not detail:
            out["purchase_cost_verification"] = "UNAVAILABLE"
            return out
        # Identity details remain useful even when shipping is unspecified.
        description = unescape(str(detail.get("description") or ""))
        out.update(full_description=re.sub(r"<[^>]+>", " ", description)[:8000],
                   purchase_detail_verified=True, purchase_detail_item_id=str(match[1]),
                   purchase_detail_url=url, purchase_detail_title=str(detail.get("title") or ""))
        if "isActive" in detail or "hasEnded" in detail or "isCancelled" in detail:
            out["listing_inactive"] = bool(detail.get("hasEnded") or detail.get("isCancelled") or detail.get("isActive") is False)
        options = [row for row in detail.get("shippingOptions") or []
                   if not row.get("isTakeaway") and not row.get("isNotSpecified")
                   and row.get("toCountryCodeIso2") == "SE"
                   and isinstance(row.get("cost"), (int, float)) and row["cost"] >= 0]
        payment = detail.get("paymentCalculations") or {}
        amount = payment.get("paymentAmountForBid")
        # The price on the category scan can have changed since ingestion.
        price = detail.get("leadingBid") or detail.get("openingBid")
        if not options or not isinstance(price, (int, float)) or price <= 0 or not isinstance(amount, (int, float)) or amount < price:
            out["purchase_cost_verification"] = "UNAVAILABLE"
            return out
        out.update(pris=price, frakt=min(row["cost"] for row in options),
                   buyer_protection_fee=round(amount - price, 2),
                   shipping_source="Tradera-annons", purchase_cost_verified=True,
                   purchase_cost_verification="VERIFIED")
        if detail.get("isAuction") and not detail.get("isPureBin"):
            out["sale_type"] = "Auktion"
        elif detail.get("isPureBin"):
            out["sale_type"] = "Köp nu"
    except (requests.RequestException, ValueError, TypeError, KeyError):
        out["purchase_cost_verification"] = "UNAVAILABLE"
    return out


def refine_purchase_costs(rows, *, limit=24):
    """Bound final verification; lower real freight can recover near misses."""
    from src.asking_price_opportunity import build_asking_price_opportunity, _cached_fx
    from src.search_progress import begin_phase, report_phase
    import time
    candidates = [row for row in rows if not row.get("purchase_cost_verified")
                  and row.get("ebay_active_context") and (row.get("lank") or row.get("url"))
                  and (row.get("asking_price_opportunity") or {}).get("comparison_count", 0) > 0
                  and (row.get("asking_price_opportunity") or {}).get("net_margin", -999) >= -29]
    candidates.sort(key=lambda row: row["asking_price_opportunity"]["net_margin"], reverse=True)
    candidates = candidates[:limit]
    begin_phase("Kontrollerar frakt och köparskydd i annonserna", len(candidates))
    for i, row in enumerate(candidates, 1):
        checked = verify_purchase_cost(row)
        row.update(checked)
        if row.get("purchase_cost_verified") or row.get("listing_inactive"):
            context = row.get("ebay_active_context") or {}
            row["asking_price_opportunity"] = build_asking_price_opportunity(row, context, fx=_cached_fx(int(time.time() // 3600)))
            scenario = row["asking_price_opportunity"]
            if scenario.get("total_cost") is not None:
                # The ranking card must show the same confirmed acquisition
                # cost as the profit scenario, including the auction buffer.
                row["analysis_total_cost"] = scenario["total_cost"]
                row["total_cost"] = round(row["pris"] + row["frakt"] + row.get("buyer_protection_fee", 0), 2)
        report_phase("Kontrollerar frakt och köparskydd i annonserna", checked=i, total=len(candidates))
    return len(candidates)
