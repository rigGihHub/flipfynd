"""Evidence-preserving funnel diagnostics for FlipFynd.

This module summarizes existing filter counters and decisions. It never changes
valuation, ranking, max bid or a candidate's decision.
"""
from __future__ import annotations
from collections import Counter


def _decision(item):
    raw = str(item.get("beslut") or item.get("decision") or "").strip().upper()
    if raw.startswith("KÖP"):
        return "KÖP"
    if raw in {"KANSKE", "BEVAKA"}:
        return "BEVAKA"
    return "SKIP"


def _primary_reason(item):
    diagnostics = item.get("decision_diagnostics") or []
    if diagnostics:
        return str(diagnostics[0]).strip()

    # Fallback only to already-computed status labels; never infer a new score.
    identity_status = str(item.get("exact_identity_gate_status") or "").strip()
    if identity_status in {"LÅST", "GRANSKA"}:
        return "Kortidentiteten behöver verifieras bättre."

    if not bool(item.get("valuation_display_safe", False)):
        return "Prisunderlaget räcker inte för en säker värdering."

    return "Når inte KÖP med nuvarande underlag."


def _category(reason):
    text = str(reason or "").casefold()
    if any(word in text for word in ("identitet", "identity", "variant", "kortnummer", "card number")):
        return "Osäker kortidentitet"
    if any(word in text for word in ("sold", "comp", "prisunderlag", "värder", "valuation", "försäljning")):
        return "För svagt prisunderlag"
    if any(word in text for word in ("vinst", "profit", "roi", "marginal", "maxpris", "max price")):
        return "För liten ekonomisk marginal"
    if any(word in text for word in ("säljbar", "liquidity", "likvid", "sale probability", "säljchans")):
        return "För låg säljbarhet"
    if any(word in text for word in ("risk", "nedsida", "downside")):
        return "För hög risk/nedsida"
    return "Övrigt"


def build_finding_funnel_diagnostic(debug, results):
    """Build a transparent funnel + decision summary from existing facts."""
    debug = debug or {}
    results = list(results or [])

    stages = [
        {"key": "total_items", "label": "Inlästa annonser", "count": int(debug.get("total_items", 0) or 0)},
        {"key": "after_sport", "label": "Rätt sport", "count": int(debug.get("after_sport", 0) or 0)},
        {"key": "valid_price", "label": "Har pris", "count": int(debug.get("valid_price", 0) or 0)},
        {"key": "within_budget", "label": "Inom budget", "count": int(debug.get("within_budget", 0) or 0)},
        {"key": "after_search", "label": "Matchar sökning", "count": int(debug.get("after_search", 0) or 0)},
        {"key": "after_sale_type", "label": "Rätt annonsform", "count": int(debug.get("after_sale_type", 0) or 0)},
        {"key": "after_feature_filters", "label": "Efter specialfilter", "count": int(debug.get("after_feature_filters", 0) or 0)},
        {"key": "final_results", "label": "Analyserade", "count": int(debug.get("final_results", len(results)) or 0)},
    ]

    biggest_drop = None
    for previous, current in zip(stages, stages[1:]):
        drop = max(0, previous["count"] - current["count"])
        if biggest_drop is None or drop > biggest_drop["drop"]:
            biggest_drop = {
                "from": previous["label"],
                "to": current["label"],
                "drop": drop,
            }

    decisions = Counter(_decision(item) for item in results)

    blocker_categories = Counter()
    raw_reasons = Counter()
    for item in results:
        if _decision(item) == "KÖP":
            continue
        reason = _primary_reason(item)
        raw_reasons[reason] += 1
        blocker_categories[_category(reason)] += 1

    category_order = [
        "Osäker kortidentitet",
        "För svagt prisunderlag",
        "För liten ekonomisk marginal",
        "För låg säljbarhet",
        "För hög risk/nedsida",
        "Övrigt",
    ]

    blockers = [
        {"label": label, "count": int(blocker_categories[label])}
        for label in category_order
        if blocker_categories[label]
    ]

    primary_reasons = [
        {"reason": reason, "count": int(count)}
        for reason, count in raw_reasons.most_common(5)
    ]

    return {
        "stages": stages,
        "biggest_drop": biggest_drop,
        "decisions": {
            "KÖP": int(decisions["KÖP"]),
            "BEVAKA": int(decisions["BEVAKA"]),
            "SKIP": int(decisions["SKIP"]),
        },
        "blockers": blockers,
        "primary_reasons": primary_reasons,
        "analysed": len(results),
        "creates_new_decision": False,
    }
