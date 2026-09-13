"""Evidence-aware candidate matching for comp research.

Ranks possible marketplace/history hits against a structured research identity.
This module is discovery-only: it never certifies exact identity, SOLD status,
valuation, max price or BUY decisions.
"""
from __future__ import annotations

import re
from typing import Iterable

from src.card_parser import parse_card_features


def _norm(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _same(a, b) -> bool:
    aa, bb = _norm(a), _norm(b)
    return bool(aa and bb and aa == bb)


def _season_key(value) -> str:
    s = _norm(value).replace(" ", "")
    m = re.fullmatch(r"((?:19|20)\d{2})(\d{2}|(?:19|20)\d{2})", s)
    if not m:
        return s
    a, b = m.groups()
    return f"{a}-{b[-2:]}"


def _set_tokens(value) -> set[str]:
    stop = {"cards", "card", "hockey", "soccer", "football", "nhl", "uefa"}
    return {t for t in _norm(value).split() if len(t) > 1 and t not in stop}


def _set_similarity(a, b) -> float:
    aa, bb = _set_tokens(a), _set_tokens(b)
    if not aa or not bb:
        return 0.0
    if aa == bb:
        return 1.0
    return len(aa & bb) / len(aa | bb)


def _features(candidate: dict) -> dict:
    title = str(candidate.get("title") or candidate.get("titel") or "")
    raw = str(candidate.get("raw_text") or candidate.get("description") or "")
    out = parse_card_features(f"{title} {raw}")
    aliases = {
        "player_name": ("player_name", "player"),
        "set_name": ("set_name", "set", "product"),
        "season": ("season", "year"),
        "card_number": ("card_number", "checklist_number"),
        "parallel": ("parallel", "variant"),
    }
    for target, keys in aliases.items():
        for key in keys:
            if candidate.get(key) not in (None, ""):
                out[target] = candidate.get(key)
                break
    for key in ("is_auto", "is_patch", "serial_denominator", "grading_company", "grade"):
        if candidate.get(key) not in (None, ""):
            out[key] = candidate.get(key)

    # Some important parallels are not always recognized by the general parser.
    # Add a small fail-closed lexical safety net so premium variants cannot
    # masquerade as the base card during research matching.
    if not out.get("parallel"):
        low = f"{title} {raw}".casefold()
        known = [
            "rink collection", "artist's proof", "artists proof",
            "silver script", "super script", "gold script",
            "red parallel", "blue parallel", "gold parallel",
            "refractor", "prizm", "holo", "young guns exclusive",
        ]
        for marker in known:
            if marker in low:
                out["parallel"] = marker.title()
                break
    return out


def match_research_candidate(identity: dict | None, candidate: dict | None) -> dict:
    """Score one hit while failing closed on hard identity conflicts."""
    target = dict(identity or {})
    candidate = dict(candidate or {})
    cf = _features(candidate)
    matches, missing, conflicts = [], [], []
    score = 0.0

    # Player + card number are strongest anchors. Explicit conflict rejects.
    for key, label, weight in (
        ("player_name", "spelare", 34),
        ("card_number", "kortnummer", 30),
    ):
        tv, cv = target.get(key), cf.get(key)
        if not tv:
            continue
        if not cv:
            missing.append(label)
        elif _same(tv, cv):
            matches.append(label); score += weight
        else:
            conflicts.append(label)

    tv, cv = target.get("season"), cf.get("season")
    if tv:
        if not cv:
            missing.append("säsong")
        elif _season_key(tv) == _season_key(cv):
            matches.append("säsong"); score += 13
        else:
            conflicts.append("säsong")

    tv, cv = target.get("set_name"), cf.get("set_name")
    if tv:
        if not cv:
            missing.append("set/program")
        else:
            sim = _set_similarity(tv, cv)
            if sim >= 0.66:
                matches.append("set/program"); score += 13
            elif sim >= 0.34:
                matches.append("set/program delvis"); score += 6
            else:
                conflicts.append("set/program")

    tv, cv = target.get("parallel"), cf.get("parallel")
    if tv:
        if not cv:
            missing.append("parallel")
        elif _same(tv, cv):
            matches.append("parallel"); score += 8
        else:
            conflicts.append("parallel")
    elif cv:
        # Candidate carries an explicit variant that target does not. This is a
        # material warning, not something to silently treat as the base card.
        conflicts.append("extra parallel")

    for key, label, weight in (("serial_denominator", "serienummer", 8), ("grading_company", "grading", 5), ("grade", "grade", 4)):
        tv, cv = target.get(key), cf.get(key)
        if not tv:
            continue
        if not cv:
            missing.append(label)
        elif _same(tv, cv):
            matches.append(label); score += weight
        else:
            conflicts.append(label)

    if target.get("is_auto"):
        if cf.get("is_auto"):
            matches.append("autograf"); score += 8
        else:
            missing.append("autograf")
    elif cf.get("is_auto"):
        conflicts.append("extra autograf")

    if target.get("is_patch"):
        if cf.get("is_patch") or cf.get("is_jersey"):
            matches.append("patch/relic"); score += 8
        else:
            missing.append("patch/relic")
    elif cf.get("is_patch") or cf.get("is_jersey"):
        conflicts.append("extra patch/relic")

    hard_conflicts = {"spelare", "kortnummer", "säsong", "parallel", "extra parallel", "serienummer", "grading", "grade", "extra autograf", "extra patch/relic"}
    has_hard_conflict = any(x in hard_conflicts for x in conflicts)
    core_match = "spelare" in matches and "kortnummer" in matches

    if has_hard_conflict or not core_match:
        label = "REJECT"
    elif score >= 86 and not conflicts and len(missing) <= 1:
        label = "STRONG_CANDIDATE"
    elif score >= 68 and not has_hard_conflict:
        label = "REVIEW"
    else:
        label = "WEAK"

    # Never call this exact; it is only candidate-ranking confidence.
    confidence = max(0, min(99, int(round(score - 12 * len(conflicts) - 4 * len(missing)))))
    return {
        "label": label,
        "candidate_confidence": confidence,
        "matches": matches,
        "missing": missing,
        "conflicts": conflicts,
        "title": candidate.get("title") or candidate.get("titel") or "",
        "url": candidate.get("url") or candidate.get("lank"),
        "source": candidate.get("source") or candidate.get("platform") or "okänd",
        "sold_claim": bool(candidate.get("sold") or candidate.get("is_sold") or candidate.get("sold_at") or candidate.get("sold_date")),
        "creates_exact_identity": False,
        "creates_sold_evidence": False,
        "note": "Kandidatmatchning rankar researchträffar. Exact identity och faktisk SOLD-status måste verifieras separat.",
    }


def rank_research_candidates(identity: dict | None, candidates: Iterable[dict] | None, *, limit: int = 8) -> list[dict]:
    rows = [match_research_candidate(identity, x) for x in (candidates or []) if isinstance(x, dict)]
    order = {"STRONG_CANDIDATE": 0, "REVIEW": 1, "WEAK": 2, "REJECT": 3}
    rows.sort(key=lambda r: (order.get(r["label"], 9), -int(r["candidate_confidence"])))
    return rows[:max(0, int(limit))]
