"""Visual identity candidate resolver for FlipFynd.

Turns Visual Card Detective hypotheses into 1–3 *candidate identities*.
Candidates are not facts and cannot affect valuation, profit, ROI, max bid or
buy decisions until independently verified. Exact verification requires
corroborating structured evidence (for example a matching sold comp) rather
than image appearance alone.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from src.card_parser import parse_card_features


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _same(a: object, b: object) -> bool:
    aa, bb = _norm(a), _norm(b)
    return bool(aa and bb and aa == bb)


def _compatible_set(a: object, b: object) -> bool:
    aa, bb = _norm(a), _norm(b)
    if not aa or not bb:
        return False
    if aa == bb or aa in bb or bb in aa:
        return True
    # Product vs insert/program naming can both be correct. These links are
    # structural identity compatibility only; they never imply value.
    links = [
        ({"upper deck series 1", "upper deck series one"}, {"young guns"}),
        ({"sp authentic"}, {"future watch", "future watch autograph"}),
        ({"o pee chee platinum", "opc platinum"}, {"marquee rookie"}),
    ]
    for products, programs in links:
        if (aa in products and bb in programs) or (bb in products and aa in programs):
            return True
    return False


def _visual_fields(findings: dict) -> dict[str, Any]:
    serial_den = findings.get("serial_denominator")
    serial_num = findings.get("serial_numerator")
    serial = None
    if isinstance(serial_num, int) and isinstance(serial_den, int) and serial_num > 0 and serial_den >= serial_num:
        serial = f"{serial_num}/{serial_den}"
    return {
        "player_name": findings.get("player_name"),
        "set_name": findings.get("set_or_product"),
        "season": findings.get("season_or_year"),
        "card_number": findings.get("card_number"),
        "parallel": findings.get("parallel_or_variant"),
        "serial": serial,
        "serial_denominator": serial_den if isinstance(serial_den, int) else None,
        "is_rookie": findings.get("rookie_marker_visible") == "yes",
        "is_auto": findings.get("autograph_visible") == "yes",
        "is_patch": findings.get("relic_or_patch_visible") == "yes",
        "grading_company": findings.get("grading_company"),
        "grade": findings.get("grade"),
    }


def _record_features(record: dict) -> dict[str, Any]:
    title = str(record.get("titel") or record.get("title") or "")
    raw = str(record.get("raw_text") or "")
    f = parse_card_features(f"{title} {raw}")
    # Imported sold comps may already carry structured identity fields.
    aliases = {
        "player_name": ("player_name", "player"),
        "set_name": ("set_name", "set", "product"),
        "season": ("season", "year"),
        "card_number": ("card_number", "checklist_number"),
        "parallel": ("parallel", "variant"),
        "grading_company": ("grading_company",),
        "grade": ("grade",),
    }
    for target, keys in aliases.items():
        for key in keys:
            if record.get(key) not in (None, ""):
                f[target] = record.get(key)
                break
    if record.get("serial_denominator") not in (None, ""):
        try:
            f["serial_denominator"] = int(record["serial_denominator"])
        except (TypeError, ValueError):
            pass
    elif f.get("serial_number"):
        f["serial_denominator"] = f.get("serial_number")
    return f


def _identity_label(fields: dict[str, Any]) -> str:
    parts: list[str] = []
    if fields.get("player_name"):
        parts.append(str(fields["player_name"]))
    if fields.get("set_name"):
        parts.append(str(fields["set_name"]))
    if fields.get("season"):
        parts.append(str(fields["season"]))
    if fields.get("card_number"):
        num = str(fields["card_number"]).lstrip("#")
        parts.append(f"#{num}")
    if fields.get("parallel"):
        parts.append(str(fields["parallel"]))
    if fields.get("serial"):
        parts.append(str(fields["serial"]))
    if fields.get("is_auto"):
        parts.append("Auto")
    if fields.get("is_patch"):
        parts.append("Patch/Relic")
    grade = " ".join(str(x) for x in (fields.get("grading_company"), fields.get("grade")) if x)
    if grade:
        parts.append(grade)
    return " • ".join(parts) or "Otillräckligt underlag"


def _match_observed_record(visual: dict[str, Any], record: dict) -> tuple[int, list[str], list[str]]:
    rf = _record_features(record)
    score = 0
    matches: list[str] = []
    conflicts: list[str] = []
    weighted = [
        ("player_name", 22, "spelare"),
        ("set_name", 18, "set/produkt"),
        ("season", 12, "säsong/år"),
        ("card_number", 28, "kortnummer"),
        ("parallel", 14, "parallel"),
        ("grading_company", 5, "grading"),
        ("grade", 5, "grade"),
    ]
    for key, weight, label in weighted:
        vv, rv = visual.get(key), rf.get(key)
        if vv in (None, "") or rv in (None, ""):
            continue
        is_match = _compatible_set(vv, rv) if key == "set_name" else _same(vv, rv)
        if is_match:
            score += weight
            matches.append(label)
        else:
            conflicts.append(label)
            score -= weight
    vd = visual.get("serial_denominator")
    rd = rf.get("serial_denominator")
    if vd and rd:
        if int(vd) == int(rd):
            score += 16
            matches.append("serienämnare")
        else:
            score -= 24
            conflicts.append("serienämnare")
    if visual.get("is_rookie") and rf.get("is_rookie"):
        score += 4
        matches.append("rookie")
    if visual.get("is_auto") and rf.get("is_auto"):
        score += 6
        matches.append("autograf")
    if visual.get("is_patch") and (rf.get("is_patch") or rf.get("is_jersey")):
        score += 6
        matches.append("patch/relic")
    return max(0, min(100, score)), matches, conflicts


def build_visual_card_candidates(
    findings: dict,
    *,
    listing_title: str = "",
    listing_raw_text: str = "",
    observed_records: Iterable[dict] | None = None,
    max_candidates: int = 3,
) -> dict:
    """Build cautious identity candidates from visual hypotheses + evidence.

    `observed_records` should preferably be verified sold-comparable records.
    A visual-only candidate can be suggested, but it is never marked verified.
    """
    findings = findings or {}
    visual = _visual_fields(findings)
    overall = float(findings.get("overall_confidence") or 0)
    listing_features = parse_card_features(f"{listing_title} {listing_raw_text}")

    evidence_fields = [k for k in ("player_name", "set_name", "season", "card_number", "parallel") if visual.get(k)]
    blockers: list[str] = []
    if overall < 0.55:
        blockers.append("Bildanalysens säkerhet är för låg")
    if not visual.get("player_name"):
        blockers.append("Spelare är inte säkert identifierad")
    if not visual.get("card_number") and not (visual.get("set_name") and visual.get("season")):
        blockers.append("För få identitetsfält för exakt kortkandidat")

    candidates: list[dict] = []
    for record in list(observed_records or []):
        score, matches, conflicts = _match_observed_record(visual, record)
        if conflicts:
            continue
        # Require meaningful identity overlap, not just player name.
        if score < 45 or len(matches) < 2:
            continue
        source = str(record.get("platform") or record.get("source") or "observerad historik")
        sold = bool(record.get("sold_price") not in (None, "") or str(record.get("market_state") or "").casefold() == "sold")
        verified = sold and score >= 70 and "kortnummer" in matches and ("set/produkt" in matches or "säsong/år" in matches)
        candidates.append({
            "label": _identity_label({**visual, **{k: _record_features(record).get(k) or visual.get(k) for k in ("player_name", "set_name", "season", "card_number", "parallel", "grading_company", "grade")}}),
            "match_score": score,
            "status": "Starkt corroborerad kandidat" if verified else "Observerad kandidat",
            "verified_identity": bool(verified),
            "evidence": matches,
            "source": source,
            "source_url": record.get("url") or record.get("lank"),
            "identity_fields": {**visual, **{k: _record_features(record).get(k) or visual.get(k) for k in ("player_name", "set_name", "season", "card_number", "parallel", "grading_company", "grade", "serial_denominator")}},
        })

    # Dedupe candidate labels, keep strongest observed evidence.
    dedup: dict[str, dict] = {}
    for c in candidates:
        key = _norm(c["label"])
        if key not in dedup or c["match_score"] > dedup[key]["match_score"]:
            dedup[key] = c
    candidates = sorted(dedup.values(), key=lambda x: (x["verified_identity"], x["match_score"]), reverse=True)

    # If history has no safe match, present the composed visual identity as a
    # hypothesis only when enough evidence exists. This is intentionally not a
    # checklist verification.
    if not candidates and not blockers:
        support = []
        for key, label in [("player_name", "spelare"), ("set_name", "set/produkt"), ("season", "säsong/år"), ("card_number", "kortnummer"), ("parallel", "parallel")]:
            vv = visual.get(key)
            lv = listing_features.get(key)
            if vv and lv and _same(vv, lv):
                support.append(label + " stöds av annonstext")
        candidate_score = round(min(88, overall * 70 + len(evidence_fields) * 4 + len(support) * 3))
        candidates.append({
            "label": _identity_label(visual),
            "match_score": candidate_score,
            "status": "Visuell kortkandidat – ej verifierad",
            "verified_identity": False,
            "evidence": support or ["bildhypotes"],
            "source": "bild + annonstext",
            "source_url": None,
            "identity_fields": dict(visual),
        })

    candidates = candidates[:max(1, int(max_candidates))]
    if any(c.get("verified_identity") for c in candidates):
        status = "Stark kortkandidat hittad"
    elif candidates:
        status = "Kortkandidat behöver verifieras"
    else:
        status = "Otillräckligt underlag"

    return {
        "status": status,
        "candidates": candidates,
        "blockers": blockers,
        "safe_for_valuation": False,
        "can_search_exact_comps": bool(any(c.get("verified_identity") for c in candidates)),
        "note": "Kandidater är identitetshypoteser. Endast en corroborerad kandidat får öppna för exakt comp-sökning; ingen kandidat ändrar värdering automatiskt.",
    }
