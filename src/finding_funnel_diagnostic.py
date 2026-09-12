"""Evidence-preserving funnel diagnostics for FlipFynd.

This module summarizes existing filter counters and decisions. It never changes
valuation, ranking, max bid or a candidate's decision.

v0.12.50 normalises dynamic diagnostic text (percentages, prices, thresholds)
into stable blocker families so the UI shows real causes instead of hundreds of
near-duplicate strings ending up in "Övrigt".
"""
from __future__ import annotations
from collections import Counter, defaultdict
import re


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


def _normalised_reason_key(reason):
    """Return a stable semantic form used only for diagnostics grouping.

    Numbers are deliberately removed because strings such as "Analyssäkerhet 5%"
    and "Analyssäkerhet 24%" represent the same blocker family.
    """
    text = str(reason or "").casefold().strip()
    text = re.sub(r"[-+]?\d+(?:[.,]\d+)?\s*%", " <pct> ", text)
    text = re.sub(r"\b\d+(?:[.,]\d+)?\s*(?:kr|sek|eur|usd|gbp)\b", " <money> ", text)
    text = re.sub(r"\b\d+(?:[.,]\d+)?\b", " <num> ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _category(reason):
    text = _normalised_reason_key(reason)

    # Keep dynamic percentage/value diagnostics out of Övrigt.
    if any(word in text for word in ("analyssäkerhet", "analysis confidence", "confidence")):
        return "För låg analyssäkerhet"

    if any(word in text for word in (
        "konservativt scenario", "conservative scenario", "konservativ värdering",
        "inköpskostnad", "köp kräver minst", "purchase cost",
    )):
        return "För svag värderingsmarginal"

    if any(word in text for word in (
        "identitet", "identity", "variant", "kortnummer", "card number",
        "set/program", "säsong/år", "spelaren är inte identifierad",
    )):
        return "Osäker kortidentitet"

    if any(word in text for word in (
        "sold", "comp", "prisunderlag", "värder", "valuation", "försäljning",
        "marknadsvärde", "marknadspris",
    )):
        return "För svagt prisunderlag"

    if any(word in text for word in (
        "vinst", "profit", "roi", "marginal", "maxpris", "max price",
        "maxbud", "avkastning",
    )):
        return "För liten ekonomisk marginal"

    if any(word in text for word in (
        "säljbar", "liquidity", "likvid", "sale probability", "säljchans",
    )):
        return "För låg säljbarhet"

    if any(word in text for word in (
        "skick", "condition", "crease", "corner", "kant", "surface",
    )):
        return "För osäkert skick"

    if any(word in text for word in ("risk", "nedsida", "downside")):
        return "För hög risk/nedsida"

    return "Övrigt"


def _num(item, *keys):
    for key in keys:
        value = item.get(key)
        try:
            if value not in (None, ""):
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _decision_readiness(results):
    """Summarise independent evidence gates without pretending they are sequential.

    These are coverage/readiness counts, not a new decision funnel. Each row uses
    already-computed fields from the analyzer and therefore cannot upgrade a card.
    """
    total = len(results)
    exact_identity = 0
    any_sold = 0
    valuation_safe = 0
    confidence_ready = 0
    buy = 0

    for item in results:
        if bool(item.get("exact_identity_gate_supports_exact_comp_search")):
            exact_identity += 1

        sold_count = _num(item, "sold_comparable_count", "sold_comps")
        if sold_count is not None and sold_count > 0:
            any_sold += 1

        if bool(item.get("valuation_display_safe", False)):
            valuation_safe += 1

        confidence = _num(item, "analysis_confidence", "confidence")
        if confidence is not None:
            # Analyzer stores this as 0..1; tolerate an already-percent value.
            confidence_fraction = confidence / 100.0 if confidence > 1 else confidence
            if confidence_fraction >= 0.28:
                confidence_ready += 1

        if _decision(item) == "KÖP":
            buy += 1

    def row(key, label, count):
        return {
            "key": key,
            "label": label,
            "count": int(count),
            "share": (float(count) / total) if total else 0.0,
        }

    return [
        row("analysed", "Analyserade", total),
        row("exact_identity", "Sökbar exakt identitet", exact_identity),
        row("sold", "Minst 1 användbar SOLD", any_sold),
        row("valuation", "Säker värdering", valuation_safe),
        row("confidence", "Analyssäkerhet ≥28 %", confidence_ready),
        row("buy", "KÖP", buy),
    ]


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
    examples_by_category = defaultdict(Counter)
    for item in results:
        if _decision(item) == "KÖP":
            continue
        reason = _primary_reason(item)
        category = _category(reason)
        raw_reasons[reason] += 1
        blocker_categories[category] += 1
        examples_by_category[category][reason] += 1

    category_order = [
        "För låg analyssäkerhet",
        "Osäker kortidentitet",
        "För svagt prisunderlag",
        "För svag värderingsmarginal",
        "För liten ekonomisk marginal",
        "För låg säljbarhet",
        "För osäkert skick",
        "För hög risk/nedsida",
        "Övrigt",
    ]

    blockers = [
        {
            "label": label,
            "count": int(blocker_categories[label]),
            "examples": [
                {"reason": reason, "count": int(count)}
                for reason, count in examples_by_category[label].most_common(3)
            ],
        }
        for label in category_order
        if blocker_categories[label]
    ]

    primary_reasons = [
        {"reason": reason, "count": int(count), "category": _category(reason)}
        for reason, count in raw_reasons.most_common(8)
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
        "decision_readiness": _decision_readiness(results),
        "analysed": len(results),
        "creates_new_decision": False,
    }
