"""Unified opportunity ranking for the ordinary FlipFynd Top 5.

Research signals may move an item up the UNDERSÖK queue, but only existing
verified valuation/SOLD evidence can produce KÖP or a displayed market value.
"""
from __future__ import annotations
from datetime import datetime, timezone
import math

from src.bad_listing_hunter import build_bad_listing_signal
from src.mispricing_detector import build_mispricing_hypothesis
from src.oddity_story_hunter import build_oddity_story_signal
from src.lot_treasure_hunter import build_lot_treasure_signal


def _n(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def listing_url(item):
    for key in ("lank", "url", "link", "href", "item_url", "tradera_url"):
        value = str((item or {}).get(key) or "").strip()
        if value.startswith(("http://", "https://")):
            return value
    return None


def _freshness(item):
    """0..10; missing timestamps are neutral rather than invented."""
    raw = next((item.get(k) for k in (
        "listed_at", "created_at", "start_time", "published_at",
        "latest_scan_at", "fetched_at", "seen_at"
    ) if item.get(k)), None)
    if not raw:
        return 0.0
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        hours = max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600)
        return max(0.0, 10.0 - min(10.0, hours / 12.0))
    except (TypeError, ValueError):
        return 0.0


def build_opportunity_top5(items, limit=5):
    rows = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        url = listing_url(item)
        title = item.get("titel") or item.get("title") or "Okänt kort"
        total = item.get("analysis_total_cost")
        if total is None:
            total = item.get("total_cost")
        total = _n(total, 0.0) or None

        sold = max(0, int(_n(item.get("sold_comparable_count"))))
        valuation_safe = item.get("valuation_display_safe") is True
        market = None
        for key in ("market_value", "estimated_market_value", "safe_market_value"):
            if item.get(key) is not None:
                market = _n(item.get(key), 0.0) or None
                break
        if not valuation_safe:
            market = None

        existing_decision = str(item.get("beslut") or item.get("decision") or "").upper()

        # Asking/guide prices are NOT valuation evidence, but a low exact-card
        # asking context is useful negative evidence. It can suppress a false
        # positive when our acquisition cost is already near/above what other
        # sellers ask; it can never create market value or KÖP.
        asking_values = []
        for key in (
            "guide_price", "guide_value", "asking_price", "asking_market_price",
            "external_asking_price", "price_guide_value", "pricecharting_price",
            "sports_cards_pro_price", "ebay_asking_price",
        ):
            value = _n(item.get(key), 0.0)
            if value > 0:
                asking_values.append(value)

        # The existing asking-price engine stores richer comparison evidence in
        # asking_price_opportunity. Feed that same evidence back into Top 5
        # instead of maintaining a disconnected second shortlist.
        asking_context = item.get("asking_price_opportunity") or {}
        if isinstance(asking_context, dict):
            value = _n(asking_context.get("reference_asking_price"), 0.0)
            if value > 0:
                asking_values.append(value)
            for comparison in asking_context.get("comparisons") or []:
                if not isinstance(comparison, dict):
                    continue
                value = _n(
                    comparison.get("asking_price_sek")
                    or comparison.get("price_sek")
                    or comparison.get("price"),
                    0.0,
                )
                if value > 0:
                    asking_values.append(value)

        for value in (item.get("asking_prices") or []):
            if isinstance(value, dict):
                value = value.get("asking_price_sek") or value.get("price") or value.get("value")
            value = _n(value, 0.0)
            if value > 0:
                asking_values.append(value)
        asking_reference = min(asking_values) if asking_values else None

        verified_edge = bool(market is not None and total is not None and market > total)
        buy = bool(existing_decision in {"KÖP", "BUY"} and sold >= 2 and valuation_safe and verified_edge)

        bad = build_bad_listing_signal(item)
        mis = build_mispricing_hypothesis(item)
        odd = build_oddity_story_signal(item)
        lot = build_lot_treasure_signal(item)

        # Generic rank/player/rookie signals are discovery clues, not proof that
        # this exact card is worth money. Cap them hard when no valuation exists.
        raw_base = max(0.0, _n(item.get("opportunity_priority_score") or item.get("deal_score") or item.get("rank_score")))
        base = min(22.0 if valuation_safe else 10.0, raw_base * 0.22)
        research = 0.0
        reasons = []
        if mis.get("status") == "SUPPORTED_PRICE_GAP":
            research += 22; reasons.append("verifierad prisgap-signal")
        elif mis.get("status") == "RESEARCH_HYPOTHESIS":
            research += min(12, 4 * len(mis.get("hypothesis_types") or [])); reasons.append("mispricing-spår")
        if bad.get("candidate"):
            research += min(10, 2.5 * len(bad.get("traits") or [])); reasons.append("svagt beskriven annons")
        if odd.get("candidate"):
            research += min(14, _n(odd.get("priority_score")) * 0.14); reasons.append("oddity/story-spår")
        if lot.get("candidate"):
            research += min(8, 2 * len(lot.get("evidence_types") or [])); reasons.append("lot/paket värt kontroll")
        if item.get("is_hidden_find_candidate"):
            research += 6; reasons.append("kan vara underexponerad")
        if item.get("is_information_edge_candidate"):
            research += 6; reasons.append("informationsövertag")
        if item.get("mispriced_rookie_candidate"):
            research += 3; reasons.append("rookie underbeskriven")
        # Without SOLD-backed valuation, research signals may keep a card visible
        # but must not be strong enough to make a cheap common rookie look like
        # the best economic opportunity.
        research = min(35.0 if valuation_safe else 18.0, research)

        evidence = min(12.0, sold * 4.0)
        if valuation_safe:
            evidence += 5.0
        economic = 0.0
        if verified_edge:
            economic = min(28.0, 12.0 + 16.0 * min(1.0, (market - total) / max(total, 1.0)))
            reasons.insert(0, "verifierat värde över köpkostnad")
        elif total:
            # No verified value means we do not know that a low purchase price is
            # cheap. Penalise uncertainty rather than rewarding "rookie", fame or
            # a low sticker price.
            economic -= 12.0
            economic -= min(12.0, max(0.0, math.log10(max(total, 10.0) / 10.0) * 5.0))

        # Negative asking-price guard. A comparable asking level can only
        # DOWN-rank. Never use it to infer upside.
        asking_warning = None
        if asking_reference is not None and total is not None:
            ratio = total / max(asking_reference, 0.01)
            if ratio >= 1.0:
                economic -= min(30.0, 14.0 + (ratio - 1.0) * 10.0)
                asking_warning = "köpkostnaden är redan vid/över observerat begärt pris"
            elif ratio >= 0.70:
                economic -= 8.0
                asking_warning = "liten marginal mot observerat begärt pris"
            if asking_warning:
                reasons.append(asking_warning)

        # Commodity/base-card warning: no exact SOLD evidence + no safe valuation
        # + no strong exact-card research evidence. Such cards can fill the list
        # only as "best of the rest", never dominate it.
        strong_exact_signal = bool(
            mis.get("status") == "SUPPORTED_PRICE_GAP"
            or odd.get("known_story_matches")
            or item.get("is_information_edge_candidate")
        )
        weak_unvalued = bool(not valuation_safe and sold == 0 and not strong_exact_signal)
        if weak_unvalued:
            economic -= 12.0
            reasons.append("saknar värdebevis för exakt kort")

        freshness = _freshness(item)
        score = max(0.0, min(100.0, base + research + evidence + economic + freshness))
        certainty = min(100.0, _n(item.get("ranking_confidence_score") or item.get("deal_confidence_score")) * 0.55 + sold * 10 + (20 if valuation_safe else 0))

        net = item.get("estimated_net_profit")
        if net is None:
            net = item.get("net_profit")
        net = _n(net, 0.0) if net is not None else None

        rows.append({
            "title": title,
            "url": url,
            "tier": "VERIFIED" if buy else ("PROMISING" if score >= 45 and not weak_unvalued else "REMAINDER"),
            "decision": "KÖP" if buy else "UNDERSÖK",
            "total_cost": total,
            "market_value": market,
            "estimated_net_profit": net,
            "potential": round(score, 1),
            "certainty": round(certainty, 1),
            "sold_comps": sold,
            "asking_reference": asking_reference,
            "asking_warning": asking_warning,
            "freshness_score": round(freshness, 1),
            "primary_blocker": None if buy else ("Marknadsvärde/SOLD ännu inte verifierat" if not valuation_safe or sold < 2 else "Ekonomiskt övertag inte verifierat"),
            "reasons": list(dict.fromkeys(reasons))[:5] or ["bäst av analyserade kandidater"],
            "_source_item": item,
        })

    # Freshness is the final tiebreaker, never a substitute for economics/evidence.
    rows.sort(key=lambda r: (
        r["decision"] == "KÖP",
        not (r.get("_source_item") and not r.get("market_value") and int(r.get("sold_comps") or 0) == 0),
        r["potential"],
        r["certainty"],
        r["freshness_score"],
        -(r["total_cost"] or 10**9),
    ), reverse=True)

    deduped, seen = [], set()
    for row in rows:
        key = row["url"] or str(row["title"]).casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
        if len(deduped) >= max(0, int(limit)):
            break
    return {
        "rows": deduped,
        "note": "KÖP kräver verifierad ekonomi. UNDERSÖK rankas även med researchsignaler; färskhet används som fördel/tiebreaker.",
    }
