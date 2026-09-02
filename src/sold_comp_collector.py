"""Collector for explicit, verifiable realised-sale evidence.

The collector is intentionally conservative. It may gather sold rows from local
snapshots/exports, but it never interprets an ended/closed listing as sold.
Only rows with explicit sale evidence are admitted to the sold-comps store.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import json

from src.sold_comp_import import normalize_sold_comp, merge_sold_comps


_EXPLICIT_SOLD_STATES = {
    "sold", "såld", "completed_sold", "ended_sold", "realized", "realised",
    "completed sold", "ended sold", "avslutad såld",
}


def _float(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def _explicit_sale_state(row: dict) -> bool:
    parts = [
        row.get("market_state"), row.get("sale_status"), row.get("status"),
        row.get("listing_status"), row.get("state"),
    ]
    text = " ".join(str(x or "").casefold().strip() for x in parts).strip()
    if not text:
        return False
    tokens = set(text.split())
    return bool(tokens.intersection(_EXPLICIT_SOLD_STATES) or any(marker in text for marker in _EXPLICIT_SOLD_STATES))


def has_explicit_sold_evidence(row: dict) -> bool:
    """True only when the row contains direct evidence that a sale occurred."""
    if not isinstance(row, dict):
        return False
    sold_price = _float(row.get("sold_price"))
    if sold_price is not None and sold_price > 0:
        return True
    # A source may expose only `pris` after marking the object explicitly sold.
    # The explicit sold state is required so an ordinary asking price cannot leak
    # into the realised-sales dataset.
    price = _float(row.get("pris") if row.get("pris") not in (None, "") else row.get("price"))
    return bool(price is not None and price > 0 and _explicit_sale_state(row))


def _collector_row(row: dict) -> dict:
    clean = dict(row)
    if not _float(clean.get("sold_price")):
        value = clean.get("pris") if clean.get("pris") not in (None, "") else clean.get("price")
        clean["sold_price"] = value
    return clean


def _richness(row: dict) -> int:
    keys = (
        "sold_at", "sale_date", "ended_at", "lank", "url", "saljare", "seller",
        "sport", "source_category", "frakt", "shipping", "sold_total_price",
        "source_platform", "platform", "provenance",
    )
    return sum(1 for key in keys if row.get(key) not in (None, ""))


def _enrich_duplicates(records: list[dict], incoming: Iterable[dict]) -> list[dict]:
    """Keep the same comp id but fill safe missing metadata from richer duplicates."""
    by_id = {row.get("sold_comp_id"): row for row in records if row.get("sold_comp_id")}
    for candidate in incoming:
        comp_id = candidate.get("sold_comp_id")
        target = by_id.get(comp_id)
        if not target:
            continue
        # Never overwrite realised price fields during enrichment.
        protected = {"sold_price", "sold_total_price", "market_state", "sale_status", "sold_comp_id"}
        for key, value in candidate.items():
            if key in protected or value in (None, ""):
                continue
            if target.get(key) in (None, ""):
                target[key] = value
    return records


def collect_sold_comps(rows: Iterable[dict], *, existing=None, source_name="local_snapshot") -> dict:
    """Collect explicit sold evidence from rows and merge it into the store."""
    candidates = []
    rejected_not_sold = 0
    rejected_invalid = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or not has_explicit_sold_evidence(row):
            rejected_not_sold += 1
            continue
        try:
            normalized = normalize_sold_comp(
                _collector_row(row), provenance=f"collector:{source_name}"
            )
            candidates.append(normalized)
        except ValueError as exc:
            rejected_invalid.append({"row": index, "error": str(exc)})

    merged, added = merge_sold_comps(existing or [], candidates)
    merged = _enrich_duplicates(merged, candidates)
    return {
        "records": merged,
        "candidate_count": len(candidates),
        "added_count": added,
        "duplicate_count": max(0, len(candidates) - added),
        "not_sold_count": rejected_not_sold,
        "invalid_count": len(rejected_invalid),
        "errors": rejected_invalid,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source_name": source_name,
    }


def load_rows_from_json(path: str | Path) -> list[dict]:
    target = Path(path)
    if not target.exists():
        return []
    payload = json.loads(target.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("items", "records", "listings", "sold_comps"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []
