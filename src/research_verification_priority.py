"""Prioritise research candidates for manual/full verification.

Discovery-only. A priority score decides what to inspect first; it never creates
exact identity, SOLD evidence, valuation, max price or BUY decisions.
"""
from __future__ import annotations

from typing import Iterable


def _source_group(source: str | None) -> str:
    s = str(source or "").casefold()
    if "ebay" in s:
        return "eBay"
    if "tradera" in s:
        return "Tradera"
    if "130" in s:
        return "130 Point"
    if "fanatics" in s:
        return "Fanatics"
    if "comc" in s:
        return "COMC"
    if "card ladder" in s or "cardladder" in s:
        return "Card Ladder"
    return str(source or "okänd")


def prioritize_verification_candidates(matches: Iterable[dict] | None, *, limit: int = 5) -> list[dict]:
    """Return the candidates worth verifying first.

    Strong/review candidates are preferred; explicit SOLD claims and independent
    source groups improve priority, but neither is treated as proof.
    """
    rows = []
    for idx, raw in enumerate(matches or []):
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label") or "")
        if label not in {"STRONG_CANDIDATE", "REVIEW"}:
            continue
        conflicts = list(raw.get("conflicts") or [])
        if conflicts:
            continue
        confidence = int(raw.get("candidate_confidence") or 0)
        sold_claim = bool(raw.get("sold_claim"))
        source_group = _source_group(raw.get("source"))
        base = 55 if label == "STRONG_CANDIDATE" else 35
        score = base + round(confidence * 0.35) + (10 if sold_claim else 0)
        score = max(0, min(99, int(score)))
        row = dict(raw)
        row.update({
            "verification_priority": score,
            "verification_source_group": source_group,
            "verification_reason": (
                "Hög identitetsmatch och kandidat uppges vara SOLD – verifiera identitet + faktisk försäljning först."
                if sold_claim else
                "Hög identitetsmatch – verifiera exakt version först; SOLD-status saknas eller är inte bekräftad."
            ),
            "creates_exact_identity": False,
            "creates_sold_evidence": False,
            "creates_buy_decision": False,
            "_stable_idx": idx,
        })
        rows.append(row)

    rows.sort(key=lambda r: (-int(r["verification_priority"]), -int(r.get("candidate_confidence") or 0), r["_stable_idx"]))

    # Diversify sources where practical so first verification effort does not
    # blindly inspect five near-duplicate hits from one marketplace.
    selected, deferred, seen = [], [], set()
    for row in rows:
        group = row["verification_source_group"]
        if group not in seen:
            selected.append(row); seen.add(group)
        else:
            deferred.append(row)
        if len(selected) >= int(limit):
            break
    if len(selected) < int(limit):
        for row in deferred:
            selected.append(row)
            if len(selected) >= int(limit):
                break

    for row in selected:
        row.pop("_stable_idx", None)
    return selected
