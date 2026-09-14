"""Quality gate and audit helpers for realised sold-comparable evidence.

The purpose is deliberately narrow: distinguish records that are safe to use as
realised-sale evidence from legacy/ambiguous rows that merely *look* sold.
Nothing in this module attempts to identify the card or estimate its value.
"""
from __future__ import annotations

from collections import Counter
import re
from typing import Iterable


_VERIFIED_STATUS = {"verified"}
_ALLOWED_EVIDENCE = {
    "explicit_sold_price",
    "explicit_sold_state_and_price",
    "explicit_sold_flag",
    "explicit_sold_status",
}
_NEGATIVE_SALE_STATUSES = (
    "unsold", "not sold", "osåld", "ej såld", "completed unsold",
    "ended unsold", "not completed sale", "cancelled", "canceled",
    "withdrawn", "expired", "active", "live", "open",
)


def _status_text(value) -> str:
    text = str(value or "").casefold().strip()
    text = re.sub(r"[_-]+", " ", text)
    return " ".join(text.split())


def _contradicts_realised_sale(record: dict) -> bool:
    for key in ("sold", "is_sold", "was_sold", "completed_sale"):
        if key not in record:
            continue
        value = record.get(key)
        text = _status_text(value)
        if value is False or text in {"false", "0", "no", "nej", "unsold", "osåld"}:
            return True
    for key in ("sale_status", "status", "listing_status", "state", "market_state"):
        status = _status_text(record.get(key))
        if status and any(marker in status for marker in _NEGATIVE_SALE_STATUSES):
            return True
    return False


def _positive_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def classify_sold_comp(record: dict) -> dict:
    """Classify one stored record without upgrading ambiguous evidence.

    ``safe_for_valuation`` is intentionally strict. A numeric ``sold_price`` or
    the word ``sold`` alone is not enough; the row must have passed FlipFynd's
    verification pipeline and retain explicit evidence metadata. Explicit
    unsold/active/cancelled state always blocks valuation even on legacy rows.
    """
    if not isinstance(record, dict):
        return {
            "safe_for_valuation": False,
            "quality": "rejected",
            "reason": "not_an_object",
        }

    if _contradicts_realised_sale(record):
        return {
            "safe_for_valuation": False,
            "quality": "rejected",
            "reason": "contradictory_unsold_state",
        }

    verification = str(record.get("sold_verification_status") or "").casefold().strip()
    evidence = str(record.get("sale_evidence_type") or record.get("source_sale_evidence") or "").casefold().strip()
    sold_price_ok = _positive_number(record.get("sold_price"))
    total_ok = _positive_number(record.get("sold_total_price"))

    if verification not in _VERIFIED_STATUS:
        return {
            "safe_for_valuation": False,
            "quality": "legacy_or_unverified",
            "reason": "missing_verified_status",
        }
    if evidence not in _ALLOWED_EVIDENCE:
        return {
            "safe_for_valuation": False,
            "quality": "legacy_or_unverified",
            "reason": "missing_explicit_sale_evidence_metadata",
        }
    if not (sold_price_ok or total_ok):
        return {
            "safe_for_valuation": False,
            "quality": "rejected",
            "reason": "missing_positive_realised_price",
        }

    has_date = bool(str(record.get("sold_at") or "").strip())
    has_source = bool(str(record.get("source_platform") or record.get("acquisition_source") or record.get("provenance") or "").strip())
    has_url = bool(str(record.get("lank") or record.get("url") or "").strip())

    metadata_score = int(has_date) + int(has_source) + int(has_url)
    quality = "strong" if metadata_score >= 2 and has_date else "verified"
    return {
        "safe_for_valuation": True,
        "quality": quality,
        "reason": "verified_explicit_sale",
        "has_date": has_date,
        "has_source": has_source,
        "has_url": has_url,
    }


def is_verified_sold_comp(record: dict) -> bool:
    return bool(classify_sold_comp(record).get("safe_for_valuation"))


def audit_sold_comp_records(records: Iterable[dict]) -> dict:
    rows = list(records or [])
    quality_counts: Counter[str] = Counter()
    rejection_reasons: Counter[str] = Counter()
    safe_records = []
    blocked_records = []

    for index, record in enumerate(rows, start=1):
        result = classify_sold_comp(record)
        quality_counts[result["quality"]] += 1
        if result["safe_for_valuation"]:
            safe_records.append(record)
        else:
            rejection_reasons[result["reason"]] += 1
            blocked_records.append({
                "row": index,
                "title": (record.get("titel") or record.get("title") or "") if isinstance(record, dict) else "",
                "reason": result["reason"],
            })

    safe_count = len(safe_records)
    total = len(rows)
    return {
        "total_count": total,
        "safe_count": safe_count,
        "blocked_count": total - safe_count,
        "strong_count": quality_counts.get("strong", 0),
        "verified_count": quality_counts.get("verified", 0),
        "quality_counts": dict(quality_counts),
        "rejection_reasons": dict(rejection_reasons),
        "safe_records": safe_records,
        "blocked_records": blocked_records,
    }
