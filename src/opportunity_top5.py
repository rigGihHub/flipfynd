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
from src.top5_reality_gate import gate_and_sort
from src.opportunity_discovery_signals import opportunity_discovery_score, opportunity_discovery_signals
from src.top5_usefulness_guard import build_useful_top5


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
        # Preserve existing heuristic/guide resale context as a clearly
        # labelled indication. It is useful for discovery even when no external
        # active-price lookup succeeded, but it is never SOLD or verified value.
        heuristic_indication = None
        for key in ("expected_resale", "floor_resale", "guide_price", "guide_value", "price_guide_value"):
            value = _n(item.get(key), 0.0)
            if value > 0:
                heuristic_indication = value
                break
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

        asking_context = item.get("asking_price_opportunity") or {}
        asking_margin = _n(asking_context.get("net_margin"), 0.0) if isinstance(asking_context, dict) else 0.0
        asking_count = int(_n(asking_context.get("comparison_count"), 0) or 0) if isinstance(asking_context, dict) else 0
        asking_positive = bool(
            isinstance(asking_context, dict)
            and asking_context.get("possible_find")
            and asking_margin > 0
            and asking_count > 0
        )
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
            # A lot is a reason to inspect images, not evidence that the lot is
            # economically valuable. Only concrete card-level evidence may add
            # a small research boost; generic lot/weak-listing signals do not.
            concrete_lot_evidence = bool(
                item.get("valuable_card_tags")
                or item.get("nonstandard_value_known_matches")
                or item.get("misclassified_card_price_gap_supported")
                or item.get("mispriced_rookie_price_gap_supported")
            )
            if concrete_lot_evidence:
                research += 3
                reasons.append("lot med konkret kortsignal att kontrollera")
            else:
                reasons.append("lot/paket – innehållet måste identifieras")
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
        elif asking_positive and total:
            # Active asking is now the primary practical screening context.
            # It may rank an UNDERSÖK candidate highly, but never creates KÖP.
            economic += min(22.0, 7.0 + 15.0 * min(1.0, asking_margin / max(total, 1.0)))
            if asking_count >= 3:
                economic += 5.0
                reasons.insert(0, f"{asking_count} jämförbara aktiva priser visar möjlig marginal")
            else:
                reasons.insert(0, "aktivt jämförpris visar möjlig marginal")
        elif total:
            # No verified value means we do not know that a low purchase price is
            # cheap. Penalise uncertainty rather than rewarding "rookie", fame or
            # a low sticker price.
            economic -= 12.0
            economic -= min(12.0, max(0.0, math.log10(max(total, 10.0) / 10.0) * 5.0))

        # Generic lots must not crowd out identifiable single cards in Top 5.
        # Without a concrete card-level value signal they are a separate manual
        # image-review task, not a leading resale opportunity.
        generic_lot = bool(lot.get("candidate") and not (
            item.get("valuable_card_tags")
            or item.get("nonstandard_value_known_matches")
            or item.get("misclassified_card_price_gap_supported")
            or item.get("mispriced_rookie_price_gap_supported")
        ))
        if generic_lot:
            economic -= 24.0
            reasons.append("generisk lot utan identifierat värdekort")

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

        # Practical discovery mode: use whatever real price context exists
        # to indicate a possible find. SOLD remains strongest, but active asking,
        # guide context and comparable listing prices may support UNDERSÖK.
        # Missing evidence lowers confidence; it no longer empties the shortlist.
        price_context_count = sold + asking_count + len(asking_values)
        indication_only = bool(not buy and (
            asking_positive
            or price_context_count > 0
            or mis.get("status") == "SUPPORTED_PRICE_GAP"
        ))
        if indication_only and not asking_positive and not verified_edge:
            research += 4.0
            reasons.append("prisindikation finns – fördjupad kontroll rekommenderas")

        # A model/guide indication is weaker than external asking/SOLD, but
        # in practical discovery mode it should still affect ranking when it
        # suggests a real spread. Never promote it to KÖP.
        heuristic_margin = None
        if heuristic_indication is not None and total is not None:
            heuristic_margin = heuristic_indication - total
            if heuristic_margin > 0 and not verified_edge and not asking_positive:
                economic += min(14.0, 4.0 + 10.0 * min(1.0, heuristic_margin / max(total, 1.0)))
                reasons.append("modell/guide visar möjlig marginal – kontrollera själv")
            elif heuristic_margin <= 0:
                economic -= 10.0
                reasons.append("modell/guide visar ingen positiv marginal")

        # Practical resale signal: rank by likely spread relative to acquisition
        # cost, while keeping evidence quality separate. This prevents a famous
        # player/card signal from beating a less glamorous card with a much
        # better observable price gap.
        practical_margin = None
        practical_source = None
        if market is not None and total is not None:
            practical_margin, practical_source = market - total, "VERIFIED"
        elif asking_reference is not None and total is not None:
            practical_margin, practical_source = asking_reference - total, "ACTIVE_PRICE"
        elif heuristic_indication is not None and total is not None:
            practical_margin, practical_source = heuristic_indication - total, "MODEL_GUIDE"

        practical_roi = None
        if practical_margin is not None and total and total > 0:
            practical_roi = practical_margin / total
            if practical_margin > 0:
                source_weight = {"VERIFIED": 1.0, "ACTIVE_PRICE": 0.80, "MODEL_GUIDE": 0.45}.get(practical_source, 0.0)
                economic += min(18.0, (6.0 + 12.0 * min(1.0, practical_roi)) * source_weight)
            else:
                economic -= min(18.0, 8.0 + 10.0 * min(1.0, abs(practical_roi)))

        # Discovery-quality improvements: reward actionable economics and
        # penalise common false-positive patterns without inventing value.
        shipping_known = item.get("shipping_known")
        if shipping_known is False:
            economic -= 4.0
            reasons.append("frakt osäker")
        sale_type = str(item.get("sale_type") or "").casefold()
        bid_count = int(_n(item.get("bid_count"), 0) or 0)
        if "auktion" in sale_type and bid_count > 0:
            research += min(4.0, bid_count * 0.5)
            reasons.append("observerad budaktivitet")
        if item.get("detail_enrichment_status") == "ok":
            research += 2.0
        if item.get("visual_verification_required"):
            economic -= 3.0
        if item.get("reprint_risk") or item.get("listing_integrity_reprint_risk"):
            economic -= 30.0
            reasons.append("reprint-risk")
        if item.get("condition_risk") or item.get("damage_risk"):
            economic -= 12.0
            reasons.append("skickrisk")
        if practical_margin is not None and practical_margin > 0 and practical_roi is not None:
            # Tiny nominal spreads are less useful even at high ROI.
            if practical_margin < 20:
                economic -= 7.0
            elif practical_margin >= 50:
                economic += 4.0
            if practical_roi >= 1.0:
                economic += 3.0

        discovery_signals = opportunity_discovery_signals(item)
        discovery_score = opportunity_discovery_score(item)
        # Discovery signals are deliberately capped in final ranking. They help
        # choose what to investigate, but economics remains dominant.
        research += max(-8.0, min(12.0, discovery_score * 0.18))

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
            "tier": "VERIFIED" if buy else ("PROMISING" if (score >= 45 or indication_only) and not weak_unvalued else "REMAINDER"),
            "decision": "KÖP" if buy else "UNDERSÖK",
            "indication_only": indication_only,
            "total_cost": total,
            "market_value": market,
            "estimated_net_profit": net,
            "potential": round(score, 1),
            "certainty": round(certainty, 1),
            "sold_comps": sold,
            "asking_reference": asking_reference,
            "heuristic_indication": heuristic_indication,
            "heuristic_margin": heuristic_margin,
            "practical_margin": practical_margin,
            "practical_roi": practical_roi,
            "practical_price_source": practical_source,
            "discovery_score": discovery_score,
            "discovery_signals": discovery_signals,
            "asking_warning": asking_warning,
            "asking_positive": asking_positive,
            "asking_comparison_count": asking_count,
            "asking_net_margin": asking_margin if asking_positive else None,
            "generic_lot": generic_lot,
            "freshness_score": round(freshness, 1),
            "primary_blocker": None if buy else ("Marknadsvärde/SOLD ännu inte verifierat" if not valuation_safe or sold < 2 else "Ekonomiskt övertag inte verifierat"),
            "reasons": list(dict.fromkeys(reasons))[:5] or ["bäst av analyserade kandidater"],
            "_source_item": item,
        })

    # Freshness is the final tiebreaker, never a substitute for economics/evidence.
    rows.sort(key=lambda r: (
        r["decision"] == "KÖP",
        not r.get("generic_lot"),
        not (r.get("_source_item") and not r.get("market_value") and int(r.get("sold_comps") or 0) == 0),
        r["potential"],
        (r.get("practical_margin") if r.get("practical_margin") is not None else -10**9),
        (r.get("practical_roi") if r.get("practical_roi") is not None else -10**9),
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
    # Apply the final gate to the whole candidate pool, not only the first
    # pre-gate five. Otherwise a candidate that should be demoted can remain in
    # Top 5 simply because stronger alternatives were discarded too early.
    # Gate the full pool, then enforce usefulness. Do not let five known
    # negative-margin rows crowd out candidates whose price still needs research.
    gated_rows = gate_and_sort(rows, limit=max(limit * 20, len(rows)))
    final_rows = build_useful_top5(gated_rows, limit=limit)
    return {
        "rows": final_rows,
        "note": "KÖP kräver verifierad ekonomi. Top 5 passerar dessutom en sista reality gate som kan nedranka kandidater med svag eller motsägande prisdata.",
    }
