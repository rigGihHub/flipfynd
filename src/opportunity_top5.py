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
        verified_edge = bool(market is not None and total is not None and market > total)
        buy = bool(existing_decision in {"KÖP", "BUY"} and sold >= 2 and valuation_safe and verified_edge)

        bad = build_bad_listing_signal(item)
        mis = build_mispricing_hypothesis(item)
        odd = build_oddity_story_signal(item)
        lot = build_lot_treasure_signal(item)

        base = min(35.0, max(0.0, _n(item.get("opportunity_priority_score") or item.get("deal_score") or item.get("rank_score"))) * 0.35)
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
            research += 5; reasons.append("rookie underbeskriven")
        research = min(35.0, research)

        evidence = min(12.0, sold * 4.0)
        if valuation_safe:
            evidence += 5.0
        economic = 0.0
        if verified_edge:
            economic = min(28.0, 12.0 + 16.0 * min(1.0, (market - total) / max(total, 1.0)))
            reasons.insert(0, "verifierat värde över köpkostnad")
        elif total:
            # With no verified value, expensive star cards must not float to the
            # top merely because player/card signals are strong.
            economic -= min(16.0, max(0.0, math.log10(max(total, 10.0) / 10.0) * 7.0))

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
            "tier": "VERIFIED" if buy else ("PROMISING" if score >= 45 else "REMAINDER"),
            "decision": "KÖP" if buy else "UNDERSÖK",
            "total_cost": total,
            "market_value": market,
            "estimated_net_profit": net,
            "potential": round(score, 1),
            "certainty": round(certainty, 1),
            "sold_comps": sold,
            "freshness_score": round(freshness, 1),
            "primary_blocker": None if buy else ("Marknadsvärde/SOLD ännu inte verifierat" if not valuation_safe or sold < 2 else "Ekonomiskt övertag inte verifierat"),
            "reasons": list(dict.fromkeys(reasons))[:5] or ["bäst av analyserade kandidater"],
            "_source_item": item,
        })

    # Freshness is the final tiebreaker, never a substitute for economics/evidence.
    rows.sort(key=lambda r: (
        r["decision"] == "KÖP",
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
