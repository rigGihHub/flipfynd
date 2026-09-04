"""Manual outcome review labels for completed FlipFynd journal entries.

The review is explicitly user-supplied evidence. It is kept separate from
automatic miss classification so FlipFynd never invents identity, variant,
condition, or market explanations that are not supported by journal data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

OUTCOME_REVIEW_REASONS = {
    "identity_wrong": "Fel kortidentifiering",
    "variant_wrong": "Fel variant/parallel",
    "condition_worse": "Skicket var sämre än väntat",
    "market_decline": "Marknaden föll efter köpet",
    "demand_weaker": "Efterfrågan var svagare än väntat",
    "listing_quality": "Försäljningsannonsen kunde varit bättre",
    "fees_higher": "Avgifter/kostnader blev högre än väntat",
    "shipping_issue": "Frakt eller logistik försämrade affären",
    "other": "Annan verifierad orsak",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_review_reasons(values: Iterable[Any] | None) -> list[str]:
    """Return unique known reason keys in stable configured order."""
    if not values:
        return []
    provided = {str(value).strip() for value in values if value is not None}
    return [key for key in OUTCOME_REVIEW_REASONS if key in provided]


def reason_labels(keys: Iterable[Any] | None) -> list[str]:
    return [OUTCOME_REVIEW_REASONS[key] for key in normalize_review_reasons(keys)]


def build_outcome_review_patch(reasons: Iterable[Any] | None, note: str | None = None) -> dict[str, Any]:
    clean_reasons = normalize_review_reasons(reasons)
    clean_note = str(note or "").strip()
    return {
        "outcome_review_reasons": clean_reasons,
        "outcome_review_note": clean_note,
        "outcome_reviewed_at": _utc_now() if clean_reasons or clean_note else None,
    }
