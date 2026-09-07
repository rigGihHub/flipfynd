"""Decision-grade intake review for sold-comparable records.

v0.11.40 deliberately separates two questions that must never be conflated:
1) Was there a real completed sale at a real price?
2) Is the sold item identified precisely enough to compare with one exact card?

A row may be verified as a sale while still being unsafe as an exact comp.
This module never estimates value and never upgrades a buy decision.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from src.sold_comp_quality import is_verified_sold_comp

CORE_IDENTITY_FIELDS = ("player_name", "set_name", "season", "card_number")
VARIANT_FIELDS = ("parallel", "serial_denominator", "grading_company", "grade")


def _text(value) -> str:
    return str(value or "").strip()


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return _text(value).casefold() in {"1", "true", "yes", "ja", "verified", "reviewed", "confirmed"}


def _norm(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _text(value).casefold()).strip()


def review_sold_comp_intake(record: dict) -> dict:
    """Classify one sold row for acquisition and exact-comp readiness.

    ``sale_verified`` answers only whether the sale itself is safe evidence.
    ``exact_identity_ready`` requires explicit structured identity metadata and
    a human/source confirmation flag. Title text alone can never unlock it.
    """
    if not isinstance(record, dict):
        return {
            "status": "REJECTED",
            "sale_verified": False,
            "exact_identity_ready": False,
            "valuation_ready": False,
            "missing_identity_fields": list(CORE_IDENTITY_FIELDS),
            "blockers": ["ogiltigt radformat"],
            "warnings": [],
        }

    sale_verified = is_verified_sold_comp(record)
    missing = [field for field in CORE_IDENTITY_FIELDS if not _text(record.get(field))]
    conflicts = list(record.get("identity_conflicts") or [])
    identity_confirmed = _truthy(
        record.get("identity_verified")
        if record.get("identity_verified") is not None
        else record.get("exact_identity_confirmed")
    )
    identity_source = _text(record.get("identity_evidence_source") or record.get("identity_source"))

    blockers = []
    warnings = []
    if not sale_verified:
        blockers.append("försäljningen är inte verifierad")
    if missing:
        blockers.append("exakt kortidentitet är ofullständig")
    if conflicts:
        blockers.append("motstridig identitetsinformation finns")
    if not identity_confirmed:
        blockers.append("exakt identitet är inte uttryckligen bekräftad")
    if not identity_source:
        warnings.append("källa för identitetskontrollen saknas")

    # Special-card metadata is not mandatory for every card. But when a row
    # explicitly says it is a parallel/graded/serialised card, the relevant
    # structured field must be present before exact-ready can be true.
    if _truthy(record.get("is_parallel")) and not _text(record.get("parallel")):
        blockers.append("parallel anges men variantnamn saknas")
    if _truthy(record.get("is_serial_numbered")) and not _text(record.get("serial_denominator")):
        blockers.append("numrerat kort anges men serienämnare saknas")
    if _truthy(record.get("is_graded")) and not (
        _text(record.get("grading_company")) and _text(record.get("grade"))
    ):
        blockers.append("graderat kort anges men bolag/grade saknas")

    exact_ready = bool(sale_verified and not missing and not conflicts and identity_confirmed and not [b for b in blockers if b != "försäljningen är inte verifierad"])

    if not sale_verified:
        status = "REJECTED"
    elif exact_ready:
        status = "EXACT_READY"
    elif not missing and not conflicts:
        status = "IDENTITY_REVIEW"
    else:
        status = "SALE_ONLY"

    return {
        "status": status,
        "sale_verified": sale_verified,
        "exact_identity_ready": exact_ready,
        # This means ready to participate as an exact identity-aware comp.
        # It does not mean it automatically matches any target card.
        "valuation_ready": exact_ready,
        "missing_identity_fields": missing,
        "identity_confirmed": identity_confirmed,
        "identity_evidence_source": identity_source or None,
        "identity_conflicts": conflicts,
        "blockers": blockers,
        "warnings": warnings,
        "identity": {field: record.get(field) for field in CORE_IDENTITY_FIELDS + VARIANT_FIELDS if record.get(field) not in (None, "")},
        "note": "Verifierad försäljning och verifierad exakt kortidentitet är två separata grindar.",
    }


def sold_comp_intake_audit(records: Iterable[dict]) -> dict:
    rows = list(records or [])
    counts = Counter()
    reviewed = []
    for index, row in enumerate(rows, start=1):
        result = review_sold_comp_intake(row)
        counts[result["status"]] += 1
        reviewed.append({
            "row": index,
            "title": (row.get("titel") or row.get("title") or "") if isinstance(row, dict) else "",
            **result,
        })
    return {
        "total_count": len(rows),
        "exact_ready_count": counts["EXACT_READY"],
        "identity_review_count": counts["IDENTITY_REVIEW"],
        "sale_only_count": counts["SALE_ONLY"],
        "rejected_count": counts["REJECTED"],
        "status_counts": dict(counts),
        "records": reviewed,
    }
