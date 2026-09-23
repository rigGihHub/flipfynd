"""Bound expensive fast analysis while preserving discovery coverage."""
from __future__ import annotations

import hashlib

from src.card_listing_integrity import assess_listing_integrity
from src.seller_collector_signals import collector_signals


def _title(item):
    return str(item.get("titel") or item.get("title") or "").strip()


def _price(item):
    try:
        return float(item.get("pris") or item.get("price") or 10**12)
    except (TypeError, ValueError):
        return float(10**12)


def _stable_key(item):
    raw = str(item.get("tradera_item_id") or item.get("lank") or item.get("url") or _title(item))
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


def _newest_page(item):
    """Return the verified market-page position, where page 1 is newest."""
    for key in ("sida", "page", "tradera_page", "page_number"):
        try:
            value = int(item.get(key))
        except (AttributeError, TypeError, ValueError):
            continue
        if value >= 1:
            return value
    return None


def _priority(item):
    title = _title(item).casefold()
    signals = collector_signals(item)
    specificity = sum(token in title for token in ("#", "rookie", " rc ", "young guns", "auto", "patch", "relic", "ssp", "variation"))
    generic_mislisting = len(title) < 30 or title in {"hockeykort", "fotbollskort", "samlarkort"}
    return (
        int(signals.get("score") or 0),
        specificity * 3,
        4 if generic_mislisting else 0,
        -_price(item),
    )


def select_fast_analysis_pool(items, *, cap=480, exploration_fraction=0.20):
    """Use global merit plus position coverage and blind exploration.

    Seller profiles are normally ordered by Tradera. A stable global sort lets
    early listings win ties, so equally promising cards on late pages could be
    starved. The bounded exploration budget therefore covers evenly spaced
    inventory segments as well as deterministic blind samples.
    """
    valid = [
        item for item in (items or [])
        if isinstance(item, dict)
        and assess_listing_integrity(item)["eligible_physical_single_card"]
    ]
    cap = max(1, int(cap or 1))
    if len(valid) <= cap:
        return valid
    exploration_count = max(1, min(cap // 3, round(cap * float(exploration_fraction))))
    merit_count = cap - exploration_count
    priorities = {id(item): _priority(item) for item in valid}
    ranked = sorted(valid, key=lambda item: priorities[id(item)], reverse=True)
    protected = []
    protected_ids = set()
    # Reserve a small first-pass lane for fresh listings. Tradera results are
    # newest-first, but global merit sorting can otherwise starve page 1-2
    # listings when their titles are still sparse. This is discovery coverage
    # only; it creates no value or BUY decision.
    freshness_budget = min(max(1, cap // 20), merit_count)
    fresh = [
        item for item in valid
        if (_newest_page(item) or 10**9) <= 2
    ]
    fresh.sort(key=lambda item: (_newest_page(item) or 10**9, _stable_key(item)))
    for item in fresh[:freshness_budget]:
        if id(item) not in protected_ids:
            protected.append(item)
            protected_ids.add(id(item))

    # Reserve representation for the most important card-specific value
    # drivers.  Without this, a broad search can crowd every autograph out of
    # the bounded pass even though the same cards appear with an autograph-only
    # filter.  This is discovery coverage only; it creates no value or BUY.
    signal_names = ("autograph", "one_of_one", "serial_numbered", "patch_relic", "case_hit_ssp")
    per_signal = max(1, min(8, cap // 20))
    protected_budget = min(merit_count, max(1, cap // 4)) if merit_count else 0
    protected_budget = max(0, protected_budget - len(protected))
    for signal_name in signal_names:
        if len(protected) >= protected_budget:
            break
        matches = [
            item for item in ranked
            if signal_name in set(collector_signals(item).get("signals") or [])
            and id(item) not in protected_ids
        ]
        for item in matches[:min(per_signal, protected_budget - len(protected))]:
            protected.append(item)
            protected_ids.add(id(item))

    merit_slots = max(0, merit_count - len(protected))
    selected = protected + [item for item in ranked if id(item) not in protected_ids][:merit_slots]
    selected_ids = {id(x) for x in selected}
    remainder = [x for x in valid if id(x) not in selected_ids]

    coverage_count = min(len(remainder), max(1, round(exploration_count * 0.67)))
    # Keep one unconditional tail sample. Old/later seller pages can contain a
    # hidden card whose title has no cheap merit signal; segment winners alone
    # could otherwise favour a cheaper neighbour in that final segment.
    coverage = [remainder[-1]] if remainder else []
    segment_slots = max(0, coverage_count - len(coverage))
    for segment_index in range(segment_slots):
        start = segment_index * len(remainder) // max(1, segment_slots)
        end = (segment_index + 1) * len(remainder) // max(1, segment_slots)
        segment = remainder[start:end]
        if segment:
            winner = max(segment, key=lambda item: (priorities[id(item)], _stable_key(item)))
            if id(winner) not in {id(x) for x in coverage}:
                coverage.append(winner)

    coverage_ids = {id(x) for x in coverage}
    blind_count = max(0, exploration_count - len(coverage))
    blind_remainder = [x for x in remainder if id(x) not in coverage_ids]
    blind = sorted(blind_remainder, key=_stable_key)[:blind_count]
    return selected + coverage + blind
