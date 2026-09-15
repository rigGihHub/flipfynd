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
    selected = ranked[:merit_count]
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
