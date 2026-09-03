"""Source adapters for externally acquired realised-sale evidence.

Adapters only translate source-specific field names into FlipFynd's strict sold
comp import contract. They do not scrape, call remote APIs, infer that an ended
listing sold, or invent FX rates. This keeps acquisition replaceable without
weakening the valuation safety gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.sold_comp_import import import_sold_comp_rows


@dataclass(frozen=True)
class SourceAdapter:
    key: str
    label: str
    sold_markers: tuple[str, ...]
    field_map: dict[str, tuple[str, ...]]


def _first(row: dict, names: tuple[str, ...]):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value
    return None


def _norm(value) -> str:
    return str(value or "").casefold().strip()


COMMON_MAP = {
    "title": ("title", "titel", "name"),
    "sold_price": ("sold_price", "soldPrice", "sale_price", "price", "pris"),
    "sold_total_price": ("sold_total_price", "total_price", "total"),
    "currency": ("currency", "valuta"),
    "sold_at": ("sold_at", "sold_date", "sale_date", "ended_at", "date"),
    "url": ("url", "link", "lank"),
    "seller": ("seller", "seller_name", "saljare"),
    "shipping": ("shipping", "shipping_price", "frakt"),
    "sport": ("sport", "category", "source_category"),
    "status": ("sale_status", "status", "listing_status", "state", "market_state"),
    "sold_flag": ("sold", "is_sold", "was_sold", "completed_sale"),
    "sold_price_sek": ("sold_price_sek", "pris_sek"),
    "sold_total_price_sek": ("sold_total_price_sek", "total_sek"),
    "fx_rate_to_sek": ("fx_rate_to_sek", "sek_rate"),
}

ADAPTERS = {
    "generic": SourceAdapter(
        "generic", "Generisk verifierad export",
        ("sold", "såld", "completed_sold", "ended_sold", "realized", "realised"),
        COMMON_MAP,
    ),
    "ebay": SourceAdapter(
        "ebay", "eBay avslutade försäljningar",
        ("sold", "completed", "completed_sold"),
        COMMON_MAP,
    ),
    "tradera": SourceAdapter(
        "tradera", "Tradera verifierade avslut",
        ("sold", "såld", "avslutad såld", "ended_sold"),
        COMMON_MAP,
    ),
}


def available_adapters() -> list[dict]:
    return [{"key": a.key, "label": a.label} for a in ADAPTERS.values()]


def _explicitly_sold(row: dict, adapter: SourceAdapter) -> tuple[bool, str | None]:
    sold_flag = _first(row, adapter.field_map["sold_flag"])
    if sold_flag is True or _norm(sold_flag) in {"true", "1", "yes", "ja", "sold", "såld"}:
        return True, "explicit_sold_flag"
    status = _norm(_first(row, adapter.field_map["status"]))
    if status and any(marker in status for marker in adapter.sold_markers):
        return True, "explicit_sold_status"
    return False, None


def adapt_external_rows(rows: Iterable[dict], source_key: str) -> dict:
    """Translate source rows, admitting only rows with explicit sale evidence."""
    adapter = ADAPTERS.get(source_key)
    if adapter is None:
        raise ValueError(f"okänd sold-comp-källa: {source_key}")
    adapted, rejected = [], []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            rejected.append({"row": index, "reason": "not_an_object"})
            continue
        is_sold, evidence = _explicitly_sold(row, adapter)
        if not is_sold:
            rejected.append({"row": index, "reason": "missing_explicit_sold_evidence"})
            continue
        out = {}
        for target, names in adapter.field_map.items():
            if target in {"status", "sold_flag"}:
                continue
            value = _first(row, names)
            if value not in (None, ""):
                out[target] = value
        out["source_platform"] = adapter.label
        out["sale_status"] = "sold"
        out["source_sale_evidence"] = evidence
        adapted.append(out)
    return {"rows": adapted, "rejected": rejected, "adapted_count": len(adapted), "rejected_count": len(rejected)}


def import_external_sold_rows(rows: Iterable[dict], source_key: str, *, existing=None) -> dict:
    """Adapt then pass through the existing strict normalizer/deduplicator."""
    adapted = adapt_external_rows(rows, source_key)
    imported = import_sold_comp_rows(
        adapted["rows"], existing=existing or [], provenance=f"external_adapter:{source_key}"
    )
    imported["adapter_rejected_count"] = adapted["rejected_count"]
    imported["adapter_rejections"] = adapted["rejected"]
    imported["adapter_key"] = source_key
    return imported
