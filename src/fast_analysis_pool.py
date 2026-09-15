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
    """Use merit plus deterministic blind exploration for a bounded pool."""
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
    ranked = sorted(valid, key=_priority, reverse=True)
    selected = ranked[:merit_count]
    selected_ids = {id(x) for x in selected}
    remainder = [x for x in valid if id(x) not in selected_ids]
    exploration = sorted(remainder, key=_stable_key)[:exploration_count]
    return selected + exploration
