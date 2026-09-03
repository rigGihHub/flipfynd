"""Collector for explicit, verifiable realised-sale evidence.

The collector is intentionally conservative. It may gather sold rows from local
snapshots/exports, but it never interprets an ended/closed listing as sold.
Only rows with explicit sale evidence are admitted to the sold-comps store.

v0.11.17 adds smart local-source acquisition and explicit evidence metadata so
FlipFynd can explain *why* a row was accepted or rejected without weakening the
sold-comp safety gate.
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


def sold_evidence_type(row: dict) -> str | None:
    """Describe the direct evidence proving a realised sale, or return None."""
    if not isinstance(row, dict):
        return None
    sold_price = _float(row.get("sold_price"))
    if sold_price is not None and sold_price > 0:
        return "explicit_sold_price"
    price = _float(row.get("pris") if row.get("pris") not in (None, "") else row.get("price"))
    if price is not None and price > 0 and _explicit_sale_state(row):
        return "explicit_sold_state_and_price"
    return None


def has_explicit_sold_evidence(row: dict) -> bool:
    """True only when the row contains direct evidence that a sale occurred."""
    return sold_evidence_type(row) is not None


def _collector_row(row: dict) -> dict:
    clean = dict(row)
    if not _float(clean.get("sold_price")):
        value = clean.get("pris") if clean.get("pris") not in (None, "") else clean.get("price")
        clean["sold_price"] = value
    return clean


def _classify_rejection(row) -> str:
    if not isinstance(row, dict):
        return "not_an_object"
    price = _float(row.get("pris") if row.get("pris") not in (None, "") else row.get("price"))
    sold_price = _float(row.get("sold_price"))
    if _explicit_sale_state(row) and not ((sold_price and sold_price > 0) or (price and price > 0)):
        return "sold_state_without_price"
    if sold_price is not None and sold_price <= 0:
        return "non_positive_sold_price"
    if price is not None and price > 0:
        return "price_without_sold_evidence"
    return "missing_sold_evidence"


def _enrich_duplicates(records: list[dict], incoming: Iterable[dict]) -> list[dict]:
    """Keep the same comp id but fill safe missing metadata from richer duplicates."""
    by_id = {row.get("sold_comp_id"): row for row in records if row.get("sold_comp_id")}
    for candidate in incoming:
        comp_id = candidate.get("sold_comp_id")
        target = by_id.get(comp_id)
        if not target:
            continue
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
    rejection_reasons = {}
    for index, row in enumerate(rows, start=1):
        evidence_type = sold_evidence_type(row)
        if not isinstance(row, dict) or not evidence_type:
            rejected_not_sold += 1
            reason = _classify_rejection(row)
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            continue
        try:
            normalized = normalize_sold_comp(
                _collector_row(row), provenance=f"collector:{source_name}"
            )
            normalized["sold_verification_status"] = "verified"
            normalized["sale_evidence_type"] = evidence_type
            normalized["acquisition_source"] = source_name
            candidates.append(normalized)
        except ValueError as exc:
            rejected_invalid.append({"row": index, "error": str(exc)})
            key = "invalid_normalized_row"
            rejection_reasons[key] = rejection_reasons.get(key, 0) + 1

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
        "rejection_reasons": rejection_reasons,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source_name": source_name,
    }


def load_rows_from_json(path: str | Path) -> list[dict]:
    target = Path(path)
    if not target.exists() or not target.is_file():
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


def discover_local_sold_sources(base_dir: str | Path, *, exclude=None) -> list[Path]:
    """Return existing JSON sources that may contain sold evidence.

    This deliberately scans only a small allow-list of known FlipFynd runtime or
    import filenames. It does not crawl the internet and it never scans the sold
    comp output file itself.
    """
    base = Path(base_dir)
    excluded = {Path(p).resolve() for p in (exclude or [])}
    names = (
        "tradera_data.json",
        "tradera_history.json",
        "sold_history.json",
        "sold_snapshot.json",
        "sold_export.json",
        "completed_sales.json",
    )
    found = []
    for name in names:
        candidate = (base / name)
        if candidate.exists() and candidate.is_file() and candidate.resolve() not in excluded:
            found.append(candidate)
    imports_dir = base / "data" / "sold_imports"
    if imports_dir.exists() and imports_dir.is_dir():
        for candidate in sorted(imports_dir.glob("*.json")):
            if candidate.resolve() not in excluded:
                found.append(candidate)
    return found


def smart_collect_local_sold_comps(base_dir: str | Path, *, existing=None, exclude=None) -> dict:
    """Scan known local sources and safely merge only explicitly sold records."""
    records = list(existing or [])
    sources = discover_local_sold_sources(base_dir, exclude=exclude)
    source_reports = []
    total_candidates = total_added = total_duplicates = total_not_sold = total_invalid = 0
    aggregate_rejections = {}

    for source in sources:
        try:
            rows = load_rows_from_json(source)
            result = collect_sold_comps(rows, existing=records, source_name=source.name)
            records = result["records"]
            report = {
                "source": str(source),
                "rows": len(rows),
                "candidate_count": result["candidate_count"],
                "added_count": result["added_count"],
                "duplicate_count": result["duplicate_count"],
                "not_sold_count": result["not_sold_count"],
                "invalid_count": result["invalid_count"],
                "rejection_reasons": result.get("rejection_reasons", {}),
            }
        except (OSError, json.JSONDecodeError, UnicodeError) as exc:
            report = {"source": str(source), "error": str(exc)}
            source_reports.append(report)
            continue

        source_reports.append(report)
        total_candidates += report["candidate_count"]
        total_added += report["added_count"]
        total_duplicates += report["duplicate_count"]
        total_not_sold += report["not_sold_count"]
        total_invalid += report["invalid_count"]
        for reason, count in report["rejection_reasons"].items():
            aggregate_rejections[reason] = aggregate_rejections.get(reason, 0) + int(count)

    return {
        "records": records,
        "sources_scanned": len(sources),
        "source_reports": source_reports,
        "candidate_count": total_candidates,
        "added_count": total_added,
        "duplicate_count": total_duplicates,
        "not_sold_count": total_not_sold,
        "invalid_count": total_invalid,
        "rejection_reasons": aggregate_rejections,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
