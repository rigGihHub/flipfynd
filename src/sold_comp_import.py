"""Validated import helpers for realised comparable sales.

FlipFynd must never turn an asking price into a realised sale by inference. This
module therefore accepts only rows that explicitly contain a sold price and
rejects foreign-currency rows unless a SEK amount (or an explicit FX rate) is
provided by the source/importer.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SUPPORTED_SPORTS = {"hockey", "football"}


def _first(row: dict, *keys):
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _float(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "").replace(",", ".")
    # Keep parsing deliberately narrow; currency symbols/text should be fixed by
    # the importer instead of guessed by FlipFynd.
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_sport(value):
    text = str(value or "").casefold().strip()
    if text in {"hockey", "nhl", "ishockey"}:
        return "hockey"
    if text in {"football", "fotboll", "soccer"}:
        return "football"
    return None


def _source_category(sport):
    if sport == "hockey":
        return "Hockey - NHL"
    if sport == "football":
        return "Fotboll"
    return ""


def _currency_to_sek(row: dict, sold_price: float, sold_total: float | None):
    currency = str(_first(row, "currency", "valuta") or "SEK").upper().strip()
    if currency in {"SEK", "KR", "SEK KR"}:
        return sold_price, sold_total, currency, None

    explicit_sold_sek = _float(_first(row, "sold_price_sek", "pris_sek"))
    explicit_total_sek = _float(_first(row, "sold_total_price_sek", "total_sek"))
    if explicit_sold_sek and explicit_sold_sek > 0:
        converted_total = explicit_total_sek if explicit_total_sek and explicit_total_sek > 0 else None
        return explicit_sold_sek, converted_total, currency, "explicit_sek"

    fx = _float(_first(row, "fx_rate_to_sek", "sek_rate", "valutakurs_till_sek"))
    if fx and fx > 0:
        return sold_price * fx, (sold_total * fx if sold_total else None), currency, "explicit_fx_rate"

    raise ValueError(
        f"valuta {currency} saknar explicit SEK-pris eller fx_rate_to_sek; ingen valutakurs gissas"
    )


def _fingerprint(record: dict) -> str:
    url = str(record.get("lank") or "").strip().casefold()
    if url:
        key = f"url|{url}"
    else:
        key = "|".join(
            [
                str(record.get("source_platform") or "").casefold().strip(),
                str(record.get("titel") or "").casefold().strip(),
                str(record.get("sold_at") or "").strip(),
                f"{float(record.get('sold_price') or 0):.2f}",
                str(record.get("saljare") or "").casefold().strip(),
            ]
        )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def normalize_sold_comp(row: dict, *, provenance: str = "manual_import") -> dict:
    if not isinstance(row, dict):
        raise ValueError("raden är inte ett objekt")

    title = str(_first(row, "titel", "title", "name") or "").strip()
    if len(title) < 4:
        raise ValueError("titel saknas eller är för kort")

    sold_price = _float(_first(row, "sold_price", "soldprice", "pris", "price"))
    if not sold_price or sold_price <= 0:
        raise ValueError("positivt sold_price saknas")

    sold_total = _float(_first(row, "sold_total_price", "sold_total", "total_price"))
    shipping = _float(_first(row, "frakt", "shipping", "shipping_price"))
    if shipping is not None and shipping < 0:
        raise ValueError("frakt kan inte vara negativ")

    sold_price, sold_total, original_currency, conversion_source = _currency_to_sek(
        row, sold_price, sold_total
    )

    sold_at = str(_first(row, "sold_at", "sale_date", "sold_date", "date", "ended_at") or "").strip()
    platform = str(_first(row, "source_platform", "platform", "marketplace") or "Okänd").strip()
    url = str(_first(row, "lank", "url", "link") or "").strip()
    seller = str(_first(row, "saljare", "säljare", "seller", "seller_name") or "").strip()
    sport = _normalize_sport(_first(row, "sport", "source_category", "category"))

    record = {
        "titel": title,
        "sold_price": round(float(sold_price), 2),
        "market_state": "sold",
        "sale_status": "sold",
        "source_platform": platform,
        "provenance": provenance,
        "sold_verification_status": "verified",
        "sale_evidence_type": "explicit_sold_price",
        "acquisition_source": provenance,
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    if sold_total and sold_total > 0:
        record["sold_total_price"] = round(float(sold_total), 2)
    if shipping is not None:
        # Shipping is only safe to carry through unchanged for SEK rows. For a
        # foreign-currency row with explicit total SEK, sold_total_price is the
        # authoritative all-in amount and the original shipping is retained as
        # source metadata instead of being mixed into SEK maths.
        if original_currency in {"SEK", "KR", "SEK KR"}:
            record["frakt"] = round(float(shipping), 2)
        else:
            record["source_shipping"] = shipping
    if sold_at:
        record["sold_at"] = sold_at
    if url:
        record["lank"] = url
    if seller:
        record["saljare"] = seller
    if sport in SUPPORTED_SPORTS:
        record["sport"] = sport
        record["source_category"] = _source_category(sport)
    if original_currency not in {"SEK", "KR", "SEK KR"}:
        record["source_currency"] = original_currency
        record["currency_conversion_source"] = conversion_source

    record["sold_comp_id"] = _fingerprint(record)
    return record


def parse_import_bytes(data: bytes, filename: str) -> list[dict]:
    suffix = Path(filename or "").suffix.casefold()
    text = data.decode("utf-8-sig")
    if suffix == ".json":
        payload = json.loads(text)
        if isinstance(payload, dict):
            payload = payload.get("items") or payload.get("sold_comps") or [payload]
        if not isinstance(payload, list):
            raise ValueError("JSON måste vara en lista eller innehålla items/sold_comps")
        return [row for row in payload if isinstance(row, dict)]
    if suffix == ".csv":
        return list(csv.DictReader(io.StringIO(text)))
    raise ValueError("endast CSV och JSON stöds")


def merge_sold_comps(existing: Iterable[dict], incoming: Iterable[dict]) -> tuple[list[dict], int]:
    merged = [dict(x) for x in existing if isinstance(x, dict)]
    seen = set()
    for row in merged:
        comp_id = row.get("sold_comp_id") or _fingerprint(row)
        seen.add(comp_id)
        row.setdefault("sold_comp_id", comp_id)

    added = 0
    for row in incoming:
        comp_id = row.get("sold_comp_id") or _fingerprint(row)
        if comp_id in seen:
            continue
        clean = dict(row)
        clean["sold_comp_id"] = comp_id
        merged.append(clean)
        seen.add(comp_id)
        added += 1
    return merged, added


def import_sold_comp_rows(rows: Iterable[dict], *, existing=None, provenance="manual_import") -> dict:
    valid = []
    errors = []
    for index, row in enumerate(rows, start=1):
        try:
            valid.append(normalize_sold_comp(row, provenance=provenance))
        except ValueError as exc:
            errors.append({"row": index, "error": str(exc)})

    merged, added = merge_sold_comps(existing or [], valid)
    return {
        "records": merged,
        "valid_count": len(valid),
        "added_count": added,
        "duplicate_count": max(0, len(valid) - added),
        "error_count": len(errors),
        "errors": errors,
    }


def save_sold_comps(records: Iterable[dict], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(list(records), ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(target)
