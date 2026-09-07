"""Describe marketplace and seller concentration inside independent Exact comps.

This module is intentionally descriptive. It never creates a valuation, changes
a KÖP decision or rejects an otherwise valid Exact comp. The only hard
concentration signal is factual: all known observations come from one source or
one seller.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from src.comp_set_consistency import collapse_independent_observations


def _clean(value: object) -> str:
    return str(value or "").strip()


def _source(row: dict) -> str:
    for key in ("source_platform", "platform", "marketplace", "source"):
        value = _clean(row.get(key))
        if value:
            return value
    return ""


def _seller(row: dict) -> str:
    for key in ("saljare", "säljare", "seller", "seller_name"):
        value = _clean(row.get(key))
        if value:
            return value
    return ""


def _dimension(values: list[str], total: int, noun_single: str, noun_multi: str) -> dict[str, Any]:
    known = [v for v in values if v]
    counts = Counter(known)
    unique = len(counts)
    top_name = None
    top_count = 0
    if counts:
        top_name, top_count = counts.most_common(1)[0]

    if not known:
        status = "UNKNOWN"
        label = f"{noun_single.capitalize()} saknas"
    elif unique == 1:
        status = "SINGLE"
        label = f"En enda {noun_single}"
    else:
        status = "MULTI"
        label = f"Flera {noun_multi}"

    return {
        "status": status,
        "label": label,
        "known_count": len(known),
        "missing_count": max(0, total - len(known)),
        "unique_count": unique,
        "top_name": top_name,
        "top_count": top_count,
        "top_share": round(top_count / len(known), 4) if known else None,
        "counts": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].casefold()))),
    }


def build_comp_source_diversity(exact_rows: Iterable[dict] | None) -> dict[str, Any]:
    consistency = collapse_independent_observations(exact_rows)
    rows = consistency["rows"]
    total = len(rows)

    sources = _dimension([_source(r) for r in rows], total, "marknadsplats", "marknadsplatser")
    sellers = _dimension([_seller(r) for r in rows], total, "säljare", "säljare")

    warnings: list[str] = []
    if total and sources["status"] == "SINGLE":
        warnings.append(
            f"alla {sources['known_count']} comps med känd källa kommer från samma marknadsplats: "
            f"{sources['top_name']}"
        )
    if total and sellers["status"] == "SINGLE" and sellers["known_count"] >= 2:
        warnings.append(
            f"alla {sellers['known_count']} comps med känd säljare kommer från samma säljare: "
            f"{sellers['top_name']}"
        )
    if sources["missing_count"]:
        warnings.append(f"marknadsplats saknas för {sources['missing_count']} av {total} oberoende comps")
    if sellers["missing_count"]:
        warnings.append(f"säljare saknas för {sellers['missing_count']} av {total} oberoende comps")

    if not rows:
        status = "NO_EXACT_COMPS"
        label = "Inga Exact-comps"
    elif sources["status"] == "UNKNOWN" and sellers["status"] == "UNKNOWN":
        status = "UNKNOWN"
        label = "Källdiversitet kan inte bedömas"
    elif sources["status"] == "SINGLE" or (sellers["status"] == "SINGLE" and sellers["known_count"] >= 2):
        status = "CONCENTRATED"
        label = "Koncentrerat comp-underlag"
    else:
        status = "DESCRIBED"
        label = "Källspridning redovisad"

    return {
        "status": status,
        "label": label,
        "independent_count": total,
        "marketplaces": sources,
        "sellers": sellers,
        "warnings": warnings,
        "note": (
            "Source Diversity är ett transparenslager. Det ändrar inte värderingen eller "
            "Comp Quality Guards beslutsstatus utan visar om underlaget är koncentrerat."
        ),
    }
