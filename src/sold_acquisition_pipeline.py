"""Source-agnostic, fail-closed acquisition pipeline for realised sold-card data.

The pipeline does not scrape marketplaces. It accepts rows from permitted exports,
APIs or feeds, normalises only explicit data, deduplicates them, and routes each
accepted sale through the decision-grade identity intake before persistence.
Rejected rows remain visible in quarantine rather than disappearing silently.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Iterable

from src.sold_comp_import import normalize_sold_comp, merge_sold_comps
from src.sold_comp_intake import review_sold_comp_intake


def acquire_sold_batch(rows: Iterable[dict], *, existing=None, source_key="manual_import", batch_id=None) -> dict:
    raw = list(rows or [])
    batch_id = batch_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    accepted = []
    quarantine = []
    route_counts = Counter()

    for index, row in enumerate(raw, start=1):
        try:
            record = normalize_sold_comp(row, provenance=source_key)
        except (ValueError, TypeError) as exc:
            quarantine.append({"row": index, "reason": str(exc), "source_key": source_key})
            continue

        record["acquisition_batch_id"] = batch_id
        record["acquisition_pipeline"] = "sold_acquisition_v1"
        review = review_sold_comp_intake(record)
        record["intake_status"] = review["status"]
        record["exact_identity_ready"] = review["exact_identity_ready"]
        route_counts[review["status"]] += 1
        accepted.append(record)

    merged, added = merge_sold_comps(existing or [], accepted)
    duplicates = max(0, len(accepted) - added)
    return {
        "batch_id": batch_id,
        "source_key": source_key,
        "input_count": len(raw),
        "accepted_count": len(accepted),
        "added_count": added,
        "duplicate_count": duplicates,
        "quarantine_count": len(quarantine),
        "route_counts": dict(route_counts),
        "exact_ready_count": route_counts["EXACT_READY"],
        "review_count": route_counts["IDENTITY_REVIEW"] + route_counts["SALE_ONLY"],
        "rejected_after_normalization_count": route_counts["REJECTED"],
        "quarantine": quarantine,
        "records": merged,
        "note": "Endast explicit sold-data accepteras. Osäker identitet hålls utanför exact-comp-spåret.",
    }
