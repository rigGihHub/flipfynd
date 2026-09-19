"""Explicit asking-price scenarios. Never SOLD evidence or a verified BUY."""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from math import isfinite
import re
import time
import xml.etree.ElementTree as ET

import requests

from src.card_parser import parse_card_features
from src.card_listing_integrity import assess_listing_integrity
from src.comp_source_intelligence import exact_identity_query
from src.ebay_browse_context import configured_credentials, fetch_configured_ebay_active_context
from src.shipping_truth import resolve_shipping

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if isfinite(number) and number >= 0 else None
    except (TypeError, ValueError):
        return None


def parse_ecb_rates(xml, *, today=None):
    root = ET.fromstring(xml)
    day = next((node.get("time") for node in root.iter() if node.get("time")), None)
    age = ((today or date.today()) - date.fromisoformat(day)).days
    if not 0 <= age <= 7:
        raise ValueError("ECB rate is stale or future dated")
    rates = {node.get("currency"): float(node.get("rate")) for node in root.iter() if node.get("currency")}
    rates["EUR"] = 1.0
    if not all(isfinite(value) and value > 0 for value in rates.values()) or "SEK" not in rates:
        raise ValueError("Invalid ECB rates")
    return {"date": day, "source": ECB_URL,
            "rates_to_sek": {code: rates["SEK"] / rate for code, rate in rates.items()}}


@lru_cache(maxsize=2)
def _cached_fx(hour):
    try:
        response = requests.get(ECB_URL, timeout=4)
        response.raise_for_status()
        return parse_ecb_rates(response.text)
    except (requests.RequestException, ValueError, TypeError, ET.ParseError):
        return {"rates_to_sek": {}, "status": "FX_UNAVAILABLE"}


def build_asking_price_opportunity(item, context, *, fx=None):
    """Compare acquisition costs to the lowest usable asking price, not a sale."""
    out = {"status": "NO_COMPARISON", "possible_find": False,
           "evidence_type": "ACTIVE_ASKING_PRICE", "creates_sold_evidence": False}
    title = str(item.get("titel") or item.get("title") or "")
    integrity = assess_listing_integrity(title)
    if (not integrity["eligible_physical_single_card"] or integrity["reprint_risk"]
            or parse_card_features(title).get("is_lot")
            or re.search(r"\b(?:damaged|creased|poor|skadad|veck|repa|repig)\b", title, re.I)):
        return {**out, "status": "CONDITION_OR_PRODUCT_REVIEW"}
    rows = []
    seen = set()
    rates = (fx or {}).get("rates_to_sek") or {}
    for row in (context or {}).get("rows") or []:
        # REVIEW hits can be browsed, but incomplete identity is not price evidence.
        if not row.get("asking_comparison_eligible") or not row.get("url"):
            continue
        if row["url"] in seen:
            continue
        seen.add(row["url"])
        value = _number(row.get("price"))
        currency = str(row.get("currency") or "").upper()
        rate = 1.0 if currency == "SEK" else _number(rates.get(currency))
        if not value or not rate:
            continue
        rows.append({**row, "asking_price_sek": round(value * rate, 2)})
    if not rows:
        return {**out, "status": "NO_MATCHED_PRICES_OR_FX"}
    rows.sort(key=lambda row: row["asking_price_sek"])
    price = _number(item.get("pris", item.get("price")))
    if price is None:
        return {**out, "status": "PURCHASE_PRICE_MISSING"}
    shipping = resolve_shipping(item)
    freight = _number(shipping["shipping"])
    if freight is None:
        return {**out, "status": "SHIPPING_INVALID"}
    # Use a conservative lower-market reference rather than a single highest
    # listing. With several exact active comps, the lower quartile resists one
    # unrealistically cheap or expensive listing while staying conservative.
    prices = [row["asking_price_sek"] for row in rows]
    # Active listings are an upper-bound indication, not realised value.
    # Use the low end of exact item prices and apply a conservative haircut so
    # one expensive listing cannot manufacture a fake resale opportunity.
    if len(prices) >= 3:
        lower_index = max(0, int((len(prices) - 1) * 0.25))
        observed_reference = prices[lower_index]
        reference_method = "LOWER_QUARTILE_ACTIVE"
        reference = round(observed_reference * 0.85, 2)
    else:
        observed_reference = prices[0]
        reference_method = "SINGLE_ACTIVE_REVIEW" if len(prices) == 1 else "LOWEST_ACTIVE"
        # One active seller is too weak to create a "possible find" by itself.
        reference = round(observed_reference * 0.85, 2)
    fee = round(min(200.0, max(3.0, reference * 0.10)), 2)
    packaging = 3.0
    total = round(price + freight, 2)
    margin = round(reference - total - fee - packaging, 2)
    enough_comps_for_find = len(rows) >= 2
    return {
        **out, "status": "POSSIBLE_FIND" if margin > 0 and enough_comps_for_find else ("SINGLE_COMP_REVIEW" if margin > 0 else "NO_MARGIN"),
        "possible_find": bool(margin > 0 and enough_comps_for_find), "purchase_price": price,
        "shipping": freight, "shipping_known": shipping["known"],
        "total_cost": total, "reference_asking_price": reference, "observed_asking_price": observed_reference,
        "reference_method": reference_method,
        "selling_fee": fee, "packaging": packaging, "net_margin": margin,
        "comparison_count": len(rows), "comparisons": rows[:5],
        "asking_evidence_strength": (
            "STRONG_ACTIVE_CONTEXT" if len(rows) >= 3
            else "LIMITED_ACTIVE_CONTEXT"
        ),
        "fx_date": (fx or {}).get("date"), "fx_source": (fx or {}).get("source"),
        "fetched_at": (context or {}).get("fetched_at"),
        "note": "Begärda kortpriser, inte genomförda försäljningar. Marginalen förutsätter försäljning till jämförelsepriset och att köparen betalar vidarefrakten. Avgift 10 % (3–200 kr), emballage 3 kr. Skick och efterfrågan måste bedömas.",
    }


def asking_research_identity(item):
    parsed = parse_card_features(str(item.get("titel") or item.get("title") or ""))
    fields = dict(parsed)
    fields.update(item.get("exact_identity_gate_research_identity_fields")
                  or item.get("exact_identity_gate_identity_fields") or {})
    fields["serial_denominator"] = fields.get("serial_denominator") or parsed.get("serial_number")
    return fields


def select_asking_price_research(rows, *, limit=24):
    """Reserve a broader cheap, identifiable pool for economic screening.

    This is discovery only. Active asking prices never become SOLD evidence,
    but a low acquisition cost deserves a chance to be checked before hobby
    prestige consumes the expensive-analysis budget.
    """
    if not all(configured_credentials()):
        return []
    eligible = []
    for row in rows:
        item = row.get("source_item") or row
        identity = asking_research_identity(item)
        # Full exact identity is ideal, but discovery may use a controlled
        # relaxed route when player + card number + one of season/set is known.
        # eBay candidate matching still decides whether a returned listing is
        # eligible as price evidence.
        core = bool(identity.get("player_name") and identity.get("card_number"))
        context = bool(identity.get("season") or identity.get("set_name"))
        if not (core and context):
            continue
        integrity = assess_listing_integrity(item)
        if not integrity["eligible_physical_single_card"] or integrity["reprint_risk"] or identity.get("is_lot"):
            continue
        price = _number(item.get("pris", item.get("price")))
        if price is None:
            continue
        shipping = resolve_shipping(item)
        freight = _number(shipping.get("shipping"))
        if freight is None:
            continue
        total_cost = price + freight
        # Prioritise plausible resale gaps rather than merely the cheapest
        # sticker prices. Collector/discovery signals only route research; they
        # never create value or BUY status.
        discovery = _number(
            row.get("opportunity_priority_score")
            or row.get("deal_score")
            or row.get("rank_score")
            or row.get("collector_signal_score")
        ) or 0.0
        freshness = _number(row.get("freshness_score")) or 0.0
        sold_hint = int(_number(row.get("sold_comps")) or 0)
        # Lower tuple is researched first: cheap remains useful, but a strong
        # identity/discovery signal can beat piles of generic 10 kr base cards.
        route_score = total_cost - min(45.0, discovery * 0.35) - min(12.0, freshness) - min(15.0, sold_hint * 3.0)
        eligible.append((route_score, total_cost, -sold_hint, row))
    eligible.sort(key=lambda pair: (pair[0], pair[1], pair[2]))
    # Do not let one cheap price band consume every slot. Spread the economic
    # probes across the sorted pool so a 60–150 kr card with a large resale
    # gap can still be discovered behind many 10–30 kr base cards.
    if len(eligible) <= limit:
        chosen = eligible
    else:
        cheap_count = max(1, round(limit * 0.60))
        chosen = eligible[:cheap_count]
        remainder = eligible[cheap_count:]
        spread_slots = limit - len(chosen)
        for i in range(spread_slots):
            idx = min(len(remainder) - 1, i * len(remainder) // max(1, spread_slots))
            chosen.append(remainder[idx])
    return [dict(row, seller_deep_route="ASKING_PRICE_RESEARCH") for *_, row in chosen]


def attach_asking_price_opportunity(item):
    """Enrich full analyses only; no network request without usable identity/keys."""
    out = dict(item)
    identity = asking_research_identity(out)
    core = bool(identity.get("player_name") and identity.get("card_number"))
    context_ready = bool(identity.get("season") or identity.get("set_name"))
    if not (core and context_ready):
        return out
    client_id, client_secret = configured_credentials()
    if not client_id or not client_secret:
        return out
    try:
        context = fetch_configured_ebay_active_context(exact_identity_query(identity), identity)
        fx = _cached_fx(int(time.time() // 3600)) if any(
            row.get("asking_comparison_eligible") and row.get("currency") != "SEK"
            for row in context.get("rows") or []
        ) else None
        out["ebay_active_context"] = context
        out["asking_price_opportunity"] = build_asking_price_opportunity(out, context, fx=fx)
    except requests.HTTPError as exc:
        response = getattr(exc, "response", None)
        out["asking_price_opportunity"] = {
            "status": "COMPARISON_HTTP_ERROR",
            "possible_find": False,
            "http_status": getattr(response, "status_code", None),
            "error_type": type(exc).__name__,
            "error_stage": str(getattr(exc, "ebay_stage", "UNKNOWN")),
        }
    except requests.Timeout as exc:
        out["asking_price_opportunity"] = {
            "status": "COMPARISON_TIMEOUT", "possible_find": False,
            "error_type": type(exc).__name__,
        }
    except requests.RequestException as exc:
        out["asking_price_opportunity"] = {
            "status": "COMPARISON_REQUEST_ERROR", "possible_find": False,
            "error_type": type(exc).__name__,
        }
    except (ValueError, TypeError, KeyError) as exc:
        out["asking_price_opportunity"] = {
            "status": "COMPARISON_DATA_ERROR", "possible_find": False,
            "error_type": type(exc).__name__,
        }
    return out
