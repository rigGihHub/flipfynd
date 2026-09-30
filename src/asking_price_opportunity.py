"""Explicit asking-price scenarios. Never SOLD evidence or a verified BUY."""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from math import isfinite
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urlunsplit

import requests

from src.card_parser import parse_card_features
from src.research_title_identity import build_research_title_identity
from src.card_listing_integrity import assess_listing_integrity
from src.comp_source_intelligence import exact_identity_query
from src.ebay_browse_context import configured_credentials, fetch_configured_ebay_active_context
from src.shipping_truth import resolve_shipping
from src.description_price_identity import recover_description_identity, price_program

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
    if item.get("listing_inactive"):
        return {**out, "status": "LISTING_ENDED"}
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
        parts = urlsplit(row["url"])
        key = row.get("item_id") or urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        if key in seen:
            continue
        seen.add(key)
        value = _number(row.get("price"))
        currency = str(row.get("currency") or "").upper()
        rate = 1.0 if currency == "SEK" else _number(rates.get(currency))
        if not value or not rate:
            continue
        rows.append({**row, "asking_price_sek": round(value * rate, 2)})
    if not rows:
        context_rows = (context or {}).get("rows") or []
        eligible_rows = [row for row in context_rows if row.get("asking_comparison_eligible") and row.get("url")]
        if (context or {}).get("raw_listing_count") == 0:
            reason = "NO_SEARCH_RESULTS"
        elif not eligible_rows:
            reason = "NO_EXACT_MATCH"
        else:
            reason = "NO_CONVERTIBLE_PRICE_OR_FX"
        return {**out, "status": "NO_MATCHED_PRICES_OR_FX", "comparison_failure_reason": reason}
    rows.sort(key=lambda row: row["asking_price_sek"])
    price = _number(item.get("pris", item.get("price")))
    if price is None or price <= 0:
        return {**out, "status": "PURCHASE_PRICE_INVALID"}
    shipping = resolve_shipping(item)
    freight = _number(shipping["shipping"])
    if freight is None:
        return {**out, "status": "SHIPPING_INVALID"}
    prices = [row["asking_price_sek"] for row in rows]
    # Active listings are an upper-bound indication, not realised value.
    # Use the low end of exact item prices and apply a conservative haircut so
    # one expensive listing cannot manufacture a fake resale opportunity.
    observed_reference = prices[0]
    reference_method = "SINGLE_ACTIVE_REVIEW" if len(prices) == 1 else "LOWEST_ACTIVE"
    reference = round(observed_reference * 0.85, 2)
    fee = round(min(200.0, max(3.0, reference * 0.10)), 2)
    packaging = 3.0
    buyer_fee = _number(item.get("buyer_protection_fee")) or 0.0
    sale_text = str(item.get("sale_type") or title).casefold()
    auction = (bool(re.search(r"auktion|utropspris|ledande bud", sale_text)) and "köp nu" not in sale_text
               or bool(re.search(r"eller\s+köp\s+nu", title, re.I)))
    # Discovery uses the actual current bid. A hypothetical higher closing bid
    # is not an acquisition cost and must not hide a >=1 kr current-bid edge.
    # The UI explicitly makes these opportunities conditional on winning here.
    auction_buffer = 0.0
    total = round(price + freight + buyer_fee + auction_buffer, 2)
    margin = round(reference - total - fee - packaging, 2)
    single_comp_signal = bool(len(rows) == 1 and margin >= 1)
    # Active asking prices are not realised sales. A lone listing may signal
    # something worth researching, but it must never become a purchase-ready
    # find by itself. Two exact active comps can support a weak possible-find;
    # three or more provide materially better market context.
    evidence_sufficient = len(rows) >= 2
    possible_find = bool(margin >= 1 and evidence_sufficient)
    return {
        **out,
        "status": (
            "RESEARCH_SINGLE_ACTIVE" if single_comp_signal
            else "POSSIBLE_FIND" if possible_find
            else "NO_MARGIN" if margin < 1
            else "INSUFFICIENT_ACTIVE_EVIDENCE"
        ),
        "possible_find": possible_find,
        "weak_find_signal": single_comp_signal,
        "research_signal": bool(margin >= 1 and not evidence_sufficient),
        "minimum_net_profit": 1.0,
        "evidence_sufficient_for_possible_find": evidence_sufficient,
        "purchase_price": price,
        "buyer_protection_fee": buyer_fee, "auction_buffer": auction_buffer,
        "auction_current_bid": auction,
        "purchase_cost_verified": bool(item.get("purchase_cost_verified")),
        "condition_warning": bool(re.search(r"corner\s*wear|hörnslitage|white\s*corner|excellent\s*/\s*ex", str(item.get("full_description") or ""), re.I)),
        "shipping": freight, "shipping_known": shipping["known"],
        "total_cost": total, "reference_asking_price": reference, "observed_asking_price": observed_reference,
        "reference_method": reference_method,
        "selling_fee": fee, "packaging": packaging, "net_margin": margin,
        "comparison_count": len(rows), "comparisons": rows[:5],
        "asking_evidence_strength": (
            "STRONG_ACTIVE_CONTEXT" if len(rows) >= 3
            else ("MODERATE_ACTIVE_CONTEXT" if len(rows) == 2 else "WEAK_SINGLE_ACTIVE_CONTEXT")
        ),
        "fx_date": (fx or {}).get("date"), "fx_source": (fx or {}).get("source"),
        "fetched_at": (context or {}).get("fetched_at"),
        "note": "Begärda kortpriser, inte genomförda försäljningar. Marginalen förutsätter försäljning till jämförelsepriset och att köparen betalar vidarefrakten. Avgift 10 % (3–200 kr), emballage 3 kr. Skick och efterfrågan måste bedömas.",
    }


def asking_research_identity(item):
    title = str(item.get("titel") or item.get("title") or "")
    parsed = parse_card_features(title)
    fields = dict(parsed)
    gated = (item.get("exact_identity_gate_research_identity_fields")
             or item.get("exact_identity_gate_identity_fields") or {})
    if gated:
        # A recovered gate can contain older parser output. Literal clean-title
        # player/number conflicts must not send research for a different card.
        fields.update(gated)
        for key in ("player_name", "card_number", "parallel", "set_name", "season"):
            if parsed.get(key):
                fields[key] = parsed[key]
        if not parsed.get("card_number"):
            recovered = build_research_title_identity(title)
            fields["card_number"] = recovered["fields"].get("card_number")
    else:
        # Raw listings have not yet passed the expensive analyzer. The same
        # title recovery used by that analyzer may route research, but it
        # never establishes a verified card identity or a purchase decision.
        recovered = build_research_title_identity(title)
        if recovered.get("complete"):
            fields.update({key: value for key, value in recovered["fields"].items() if value})
        if parsed.get("set_name"):
            fields["set_name"] = parsed["set_name"]
    description_fields = recover_description_identity(item)
    fields.update(description_fields)
    fields["price_program"] = price_program(title)
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
        if item.get("listing_inactive"):
            continue
        identity = asking_research_identity(item)
        # The downstream eBay evidence gate requires player + exact card number
        # and season/set context. Routing looser identities here only consumed
        # network/deep-analysis slots that could never produce a usable price.
        has_player = bool(identity.get("player_name"))
        has_number = bool(identity.get("card_number"))
        has_season = bool(identity.get("season"))
        has_set = bool(identity.get("set_name"))
        exact_route = has_player and has_number and (has_season or has_set)
        if not exact_route:
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
        title_fold = str(item.get("titel") or item.get("title") or "").casefold()
        variant_bonus = 0.0
        if re.search(r"\b(?:rookie|\brc\b|refractor|prizm|parallel|rainbow|color wheel|silver|gold|red|blue|green|ssp|sp)\b", title_fold):
            variant_bonus += 10.0
        if re.search(r"(?<!\d)\d{1,4}\s*/\s*\d{1,4}(?!\d)|\b(?:auto|autograph|patch|relic|jersey|game[- ]used)\b", title_fold):
            variant_bonus += 18.0
        route_score = total_cost - min(45.0, discovery * 0.35) - min(12.0, freshness) - min(15.0, sold_hint * 3.0) - variant_bonus
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
        context = fetch_configured_ebay_active_context(price_lookup_query(identity), identity)
        # One shorter discovery query can recover spelling/set-title variants.
        # Both searches still pass the unchanged exact-identity matcher.
        eligible = [row for row in context.get("rows") or [] if row.get("asking_comparison_eligible")]
        # Spend a second request only on an already profitable single-price
        # lead. Empty/negative queries formerly doubled quota consumption.
        primary = build_asking_price_opportunity(out, context, fx=(
            _cached_fx(int(time.time() // 3600)) if any(
                row.get("asking_comparison_eligible") and row.get("currency") != "SEK"
                for row in context.get("rows") or []) else None))
        if len(eligible) == 1 and primary.get("research_signal"):
            shorter = " ".join(str(value) for value in (
                identity.get("player_name"), identity.get("season"),
                "#" + str(identity.get("card_number") or "")) if value)
            if shorter != price_lookup_query(identity):
                try:
                    extra = fetch_configured_ebay_active_context(shorter, identity)
                except requests.RequestException as exc:
                    # A failed optional query must not erase valid primary data.
                    extra = {}
                    context["expansion_error"] = type(exc).__name__
                seen_urls = {row.get("url") for row in context.get("rows") or []}
                context["rows"] = list(context.get("rows") or []) + [
                    row for row in extra.get("rows") or [] if row.get("url") not in seen_urls]
                context["raw_listing_count"] = int(context.get("raw_listing_count") or 0) + int(extra.get("raw_listing_count") or 0)
                context["query_expanded"] = True
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
            "retry_after_seconds": getattr(exc, "retry_after_seconds", None),
            "ebay_error_ids": getattr(exc, "ebay_error_ids", []),
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


def price_lookup_query(identity):
    """Use literal player/season/number anchors; verify the set in every hit.

    eBay sellers spell manufacturers differently (OPC/O-Pee-Chee, UD/Upper
    Deck). Mandatory manufacturer words in the request hid comparable cards.
    Removing those query words never removes the downstream exact-set gate.
    """
    fields = dict(identity)
    fields.pop("set_name", None)
    return exact_identity_query(fields)
