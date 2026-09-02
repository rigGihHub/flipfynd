from __future__ import annotations

import re
from typing import Any

from src.card_parser import parse_card_features


FIELD_LABELS = {
    "player_name": "spelare",
    "set_name": "set/program",
    "season": "säsong",
    "year": "år",
    "card_number": "kortnummer",
    "parallel": "parallel/variant",
    "serial_number": "serienämnare",
    "grade": "grade",
    "grading_company": "grading",
    "is_rookie": "rookie",
    "is_auto": "autograf",
    "is_patch": "patch",
    "is_jersey": "jersey/relic",
    "is_1of1": "1/1",
}

SOURCE_WEIGHTS = {
    "title": 46,
    "listing_text": 26,
    "detail_description": 34,
    "visual": 24,
}


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _same(field: str, a: Any, b: Any) -> bool:
    if a in (None, "") or b in (None, ""):
        return False
    if field in {"is_rookie", "is_auto", "is_patch", "is_jersey", "is_1of1"}:
        return bool(a) == bool(b)
    if field == "serial_number":
        try:
            return int(a) == int(b)
        except (TypeError, ValueError):
            return _norm(a) == _norm(b)
    aa, bb = _norm(a), _norm(b)
    return bool(aa and bb and (aa == bb or (field == "set_name" and (aa in bb or bb in aa))))


def _visual_features(findings: dict | None) -> dict:
    findings = findings or {}
    out = {
        "player_name": findings.get("player_name"),
        "set_name": findings.get("set_or_product"),
        "season": findings.get("season_or_year"),
        "card_number": findings.get("card_number"),
        "parallel": findings.get("parallel_or_variant"),
        "grading_company": findings.get("grading_company"),
        "grade": findings.get("grade"),
        "is_rookie": findings.get("rookie_marker_visible") == "yes",
        "is_auto": findings.get("autograph_visible") == "yes",
        "is_patch": findings.get("relic_or_patch_visible") == "yes",
    }
    den = findings.get("serial_denominator")
    if den not in (None, ""):
        try:
            out["serial_number"] = int(den)
            out["is_1of1"] = int(den) == 1
        except (TypeError, ValueError):
            pass
    return out


def _source_payload(item: dict, visual_findings: dict | None = None) -> dict[str, dict]:
    title = str(item.get("titel") or "")
    raw = str(item.get("raw_text") or "")
    detail = str(item.get("full_description") or "")
    payload = {
        "title": parse_card_features(title),
        "listing_text": parse_card_features(raw),
        "detail_description": parse_card_features(detail),
    }
    if visual_findings:
        payload["visual"] = _visual_features(visual_findings)
    return payload


def build_detail_evidence_fusion(
    item: dict | None,
    *,
    visual_findings: dict | None = None,
) -> dict[str, Any]:
    """Fuse identity evidence without converting hypotheses into valuation facts.

    Title, category/listing text, detail description and optional visual findings
    are kept as separate evidence sources. The result is for identity review and
    hunter guardrails only; it must not create prices, ROI, profit or max bids.
    """
    item = item or {}
    sources = _source_payload(item, visual_findings)
    fields = list(FIELD_LABELS)
    support: dict[str, list[dict]] = {}
    conflicts: list[str] = []
    discoveries: list[str] = []
    corroborated: list[str] = []

    for field in fields:
        observations = []
        for source, features in sources.items():
            value = features.get(field)
            if field.startswith("is_"):
                if not value:
                    continue
            elif value in (None, ""):
                continue
            observations.append({"source": source, "value": value, "weight": SOURCE_WEIGHTS[source]})
        if observations:
            support[field] = observations

        title_obs = next((x for x in observations if x["source"] == "title"), None)
        detail_obs = next((x for x in observations if x["source"] == "detail_description"), None)
        visual_obs = next((x for x in observations if x["source"] == "visual"), None)

        if detail_obs and not title_obs:
            discoveries.append(f"Detaljbeskrivningen tillför {FIELD_LABELS[field]}: {detail_obs['value']}")
        if visual_obs and not title_obs and not detail_obs:
            discoveries.append(f"Bilden antyder {FIELD_LABELS[field]}: {visual_obs['value']}")

        for i, left in enumerate(observations):
            for right in observations[i + 1:]:
                if _same(field, left["value"], right["value"]):
                    pair = {left["source"], right["source"]}
                    if "detail_description" in pair and ("title" in pair or "visual" in pair):
                        corroborated.append(FIELD_LABELS[field])
                else:
                    # Boolean absence is not evidence of conflict; only explicit observations reach here.
                    conflicts.append(
                        f"{FIELD_LABELS[field]} skiljer sig: {left['source']}={left['value']} / {right['source']}={right['value']}"
                    )

    # Score evidence quality, not card value. Strongest when exact identity fields
    # are independently corroborated by title/detail and optionally visual review.
    score = 0
    key_fields = ("player_name", "set_name", "card_number", "parallel", "serial_number")
    for field in key_fields:
        obs = support.get(field, [])
        if not obs:
            continue
        score += min(16, max(x["weight"] for x in obs) // 4)
        if len(obs) >= 2 and any(_same(field, obs[0]["value"], x["value"]) for x in obs[1:]):
            score += 7
    if support.get("season") or support.get("year"):
        score += 7
    if visual_findings and float(visual_findings.get("overall_confidence") or 0) >= 0.7:
        score += 6
    if conflicts:
        score -= min(50, 22 + 10 * (len(conflicts) - 1))
    score = max(0, min(100, int(round(score))))

    if conflicts:
        status = "Konflikt – verifiera manuellt"
    elif score >= 80 and len(set(corroborated)) >= 2:
        status = "Starkt fler-källestöd"
    elif score >= 60:
        status = "Bra stöd – kontrollera exakt variant"
    elif score >= 40:
        status = "Delvis stöd"
    else:
        status = "Otillräckligt underlag"

    return {
        "score": score,
        "status": status,
        "source_count": sum(1 for name, data in sources.items() if any(v not in (None, "", False) for v in data.values())),
        "sources": sources,
        "field_support": support,
        "corroborated_fields": sorted(set(corroborated)),
        "discoveries": list(dict.fromkeys(discoveries))[:8],
        "conflicts": list(dict.fromkeys(conflicts))[:8],
        "has_conflict": bool(conflicts),
        "visual_included": bool(visual_findings),
        "safe_for_valuation": False,
        "note": (
            "Evidence Fusion väger bara identitetsbevis från titel, annonsinfo, detaljbeskrivning och eventuell bildanalys. "
            "Den skapar inte marknadsvärde, vinst, ROI, maxbud eller köpbeslut."
        ),
    }
