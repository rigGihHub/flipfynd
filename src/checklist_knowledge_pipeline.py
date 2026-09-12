"""Curated checklist-knowledge ingestion and quality control.

The pipeline is deliberately conservative: it can merge source-backed structural
knowledge, detect duplicate/conflicting rarity claims and report coverage gaps,
but it never converts a checklist claim into market value.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

OFFICIAL_HOSTS = {
    "upperdeck.com", "www.upperdeck.com",
    "topps.com", "www.topps.com",
    "paniniamerica.net", "www.paniniamerica.net",
}


def _norm(v: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(v or "").casefold()).strip()


def is_official_source_url(url: str | None) -> bool:
    try:
        host = urlparse(str(url or "")).hostname or ""
    except Exception:
        return False
    host = host.casefold()
    return host in OFFICIAL_HOSTS or host.endswith(".topps.com") or host.endswith(".upperdeck.com") or host.endswith(".paniniamerica.net")


def _signal_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        _norm(row.get("sport")),
        _norm(row.get("product_family")),
        _norm(row.get("program_family") or row.get("label")),
        _norm(row.get("label")),
    )


def validate_signal(row: dict[str, Any], source_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if not _norm(row.get("label")):
        errors.append("missing_label")
    if not _norm(row.get("sport")):
        errors.append("missing_sport")
    if not _norm(row.get("product_family")):
        errors.append("missing_product_family")
    if not (row.get("patterns") or row.get("patterns_any") or row.get("program_family")):
        errors.append("missing_match_pattern")
    source_id = str(row.get("source_id") or "").strip()
    if not source_id:
        errors.append("missing_source_id")
    elif source_id not in source_ids:
        errors.append("unknown_source_id")
    run = row.get("print_run")
    if run not in (None, ""):
        try:
            if int(run) <= 0:
                errors.append("invalid_print_run")
        except (TypeError, ValueError):
            errors.append("invalid_print_run")
    for field in ("packs_per_box", "boxes_per_case"):
        value = row.get(field)
        if value not in (None, ""):
            try:
                if int(value) <= 0:
                    errors.append(f"invalid_{field}")
            except (TypeError, ValueError):
                errors.append(f"invalid_{field}")
    return errors


def audit_knowledge(knowledge: dict[str, Any]) -> dict[str, Any]:
    sources = [dict(s) for s in knowledge.get("sources", []) if isinstance(s, dict)]
    signals = [dict(s) for s in knowledge.get("signals", []) if isinstance(s, dict)]
    source_ids = {str(s.get("id")) for s in sources if s.get("id")}
    invalid_sources = [
        {"id": s.get("id"), "url": s.get("url")}
        for s in sources
        if not s.get("id") or not is_official_source_url(s.get("url"))
    ]
    invalid_signals = []
    legacy_gaps = []
    for idx, row in enumerate(signals):
        errs = validate_signal(row, source_ids)
        # Older curated rows may predate source IDs/product-family metadata. Keep
        # those visible as research debt without declaring the whole knowledge
        # base structurally invalid. New ingestion remains strict via merge_knowledge.
        soft = {"missing_source_id", "missing_product_family"}
        hard = [e for e in errs if e not in soft]
        if hard:
            invalid_signals.append({"index": idx, "label": row.get("label"), "errors": hard})
        if any(e in soft for e in errs):
            legacy_gaps.append({"index": idx, "label": row.get("label"), "gaps": [e for e in errs if e in soft]})

    by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for row in signals:
        by_key.setdefault(_signal_key(row), []).append(row)
    duplicates = []
    conflicts = []
    for key, rows in by_key.items():
        if len(rows) > 1:
            duplicates.append({"key": key, "labels": [r.get("label") for r in rows]})
        runs = {int(r["print_run"]) for r in rows if str(r.get("print_run") or "").isdigit()}
        odds = {_norm(r.get("pull_odds") or r.get("published_odds")) for r in rows if r.get("pull_odds") or r.get("published_odds")}
        if len(runs) > 1 or len(odds) > 1:
            conflicts.append({"key": key, "print_runs": sorted(runs), "odds": sorted(odds)})

    products: dict[str, dict[str, Any]] = {}
    for row in signals:
        prod = str(row.get("product_family") or "Unknown")
        p = products.setdefault(prod, {"signals": 0, "objective": 0, "sourced": 0, "format_configured": 0, "sports": set(), "categories": set()})
        p["signals"] += 1
        p["sports"].add(str(row.get("sport") or "unknown"))
        p["categories"].add(str(row.get("category") or "unknown"))
        if row.get("print_run") not in (None, "") or row.get("pull_odds") or row.get("published_odds"):
            p["objective"] += 1
        if row.get("source_id") in source_ids:
            p["sourced"] += 1
        if row.get("packs_per_box") not in (None, "") and row.get("boxes_per_case") not in (None, ""):
            p["format_configured"] += 1
    coverage = []
    for prod, stats in sorted(products.items()):
        coverage.append({
            "product_family": prod,
            "signals": stats["signals"],
            "objective_signals": stats["objective"],
            "source_backed_signals": stats["sourced"],
            "format_configured_signals": stats["format_configured"],
            "sports": sorted(stats["sports"]),
            "categories": sorted(stats["categories"]),
        })

    return {
        "source_count": len(sources),
        "signal_count": len(signals),
        "invalid_source_count": len(invalid_sources),
        "invalid_signal_count": len(invalid_signals),
        "duplicate_key_count": len(duplicates),
        "conflict_count": len(conflicts),
        "invalid_sources": invalid_sources[:20],
        "invalid_signals": invalid_signals[:20],
        "legacy_gap_count": len(legacy_gaps),
        "legacy_gaps": legacy_gaps[:30],
        "duplicates": duplicates[:20],
        "conflicts": conflicts[:20],
        "product_coverage": coverage,
        "healthy": not invalid_sources and not invalid_signals and not conflicts,
        "note": "Audit mäter käll- och strukturkvalitet, inte marknadsvärde eller efterfrågan.",
    }


def merge_knowledge(base: dict[str, Any], *, sources: Iterable[dict] = (), signals: Iterable[dict] = ()) -> dict[str, Any]:
    out = deepcopy(base)
    out.setdefault("sources", [])
    out.setdefault("signals", [])
    source_map = {str(s.get("id")): s for s in out["sources"] if s.get("id")}
    for source in sources:
        row = dict(source)
        sid = str(row.get("id") or "").strip()
        if not sid:
            raise ValueError("source requires id")
        if not is_official_source_url(row.get("url")):
            raise ValueError(f"source {sid} is not on an approved official host")
        source_map[sid] = row
    out["sources"] = list(source_map.values())
    source_ids = set(source_map)

    existing = {_signal_key(s): s for s in out["signals"]}
    for signal in signals:
        row = dict(signal)
        errors = validate_signal(row, source_ids)
        if errors:
            raise ValueError(f"invalid signal {row.get('label')!r}: {', '.join(errors)}")
        key = _signal_key(row)
        prev = existing.get(key)
        if prev:
            prev_run = prev.get("print_run")
            new_run = row.get("print_run")
            if prev_run not in (None, "") and new_run not in (None, "") and int(prev_run) != int(new_run):
                raise ValueError(f"conflicting print_run for {row.get('label')}: {prev_run} vs {new_run}")
        existing[key] = row
    out["signals"] = list(existing.values())
    return out


def load_knowledge(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_knowledge(path: str | Path, knowledge: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(knowledge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
