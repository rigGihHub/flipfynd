"""Exact Identity Gate for FlipFynd.

Central safety gate used before exact sold comps or a comp-supported dynamic
max bid may be treated as decision-grade evidence.  The gate never estimates
value and never upgrades a buy decision; it only decides whether identity
evidence is complete and internally consistent enough for downstream tools.
"""
from __future__ import annotations

from typing import Any


def _text(value: object) -> str:
    return str(value or "").strip()


def _num(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: object) -> bool:
    return bool(value)


def build_exact_identity_gate(data: dict[str, Any] | None) -> dict[str, Any]:
    """Return a conservative identity verdict without any monetary inference.

    Two downstream permissions are intentionally separate:
      * ``supports_exact_comp_search``: enough identity to search/classify exact comps.
      * ``supports_dynamic_max_bid``: stricter multi-source identity support before
        exact comps may be used to tighten a pre-existing bid ceiling.
    """
    d = dict(data or {})

    player = _text(d.get("player_name"))
    player_conf = _text(d.get("player_match_confidence") or "low").casefold()
    set_name = _text(d.get("set_name") or d.get("card_set"))
    season = _text(d.get("season") or d.get("year"))
    card_number = _text(d.get("card_number") or d.get("checklist_number"))
    parallel = _text(d.get("parallel"))
    grade = _text(d.get("grade"))
    grading_company = _text(d.get("grading_company"))
    serial = d.get("serial_number")
    identity_score = _num(
        d.get("card_identity_confidence_score", d.get("identity_confidence_score", 0)), 0
    )

    identity_conflicts = list(d.get("identity_conflicts") or [])
    fusion_conflicts = list(d.get("detail_evidence_fusion_conflicts") or [])
    has_fusion_conflict = _bool(d.get("detail_evidence_fusion_has_conflict")) or bool(fusion_conflicts)
    conflicts = identity_conflicts + fusion_conflicts

    evidence_sources = d.get("identity_evidence_sources") or {}
    source_names: set[str] = set()
    if isinstance(evidence_sources, dict):
        for values in evidence_sources.values():
            if isinstance(values, (list, tuple, set)):
                source_names.update(_text(v) for v in values if _text(v))
    fusion_source_count = int(_num(d.get("detail_evidence_fusion_source_count"), 0))
    source_count = max(len(source_names), fusion_source_count)

    is_special = any([
        parallel,
        serial not in (None, ""),
        _bool(d.get("is_auto")),
        _bool(d.get("is_patch")),
        _bool(d.get("is_jersey")),
        _bool(d.get("is_1of1")),
        grade,
        grading_company,
    ])

    missing: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    strengths: list[str] = []

    if not player:
        missing.append("spelare")
        blockers.append("spelare saknas")
    elif player_conf != "high":
        blockers.append("spelaren är inte identifierad med hög säkerhet")
    else:
        strengths.append("spelare identifierad med hög säkerhet")

    if not set_name:
        missing.append("set/program")
        blockers.append("set eller kortprogram saknas")
    else:
        strengths.append("set/program identifierat")

    if not season:
        missing.append("säsong/år")
        blockers.append("säsong eller år saknas")
    else:
        strengths.append("säsong/år identifierat")

    if not card_number:
        missing.append("kortnummer")
        blockers.append("kortnummer saknas")
    else:
        strengths.append("kortnummer identifierat")

    if conflicts or has_fusion_conflict:
        blockers.append("motstridig identitetsinformation finns mellan källor")

    if d.get("is_lot"):
        blockers.append("lot/multipack får inte låsa upp exakt kortidentitet")

    if is_special and not (parallel or serial not in (None, "") or grade or grading_company):
        warnings.append("specialkort indikeras men exakt variant/numrering/gradering är inte strukturerad")

    if identity_score >= 90:
        strengths.append(f"kortidentifiering {identity_score:.0f}/100")
    elif identity_score >= 80:
        warnings.append(f"kortidentifiering {identity_score:.0f}/100 – nära stark nivå")
    else:
        warnings.append(f"kortidentifiering endast {identity_score:.0f}/100")

    if source_count >= 2:
        strengths.append(f"identiteten stöds av {source_count} evidenskällor")
    elif source_count == 1:
        warnings.append("identiteten bygger huvudsakligen på en evidenskälla")
    else:
        warnings.append("ingen tydlig källseparation finns för identitetsfälten")

    critical_complete = bool(player and set_name and season and card_number and player_conf == "high")
    conflict_free = not blockers or all(
        b not in {
            "motstridig identitetsinformation finns mellan källor",
            "lot/multipack får inte låsa upp exakt kortidentitet",
        }
        for b in blockers
    )
    # More explicit and safer than the generic conflict_free expression above.
    conflict_free = not conflicts and not has_fusion_conflict and not d.get("is_lot")

    supports_exact = bool(critical_complete and conflict_free and identity_score >= 78)
    supports_dynamic = bool(supports_exact and identity_score >= 88 and source_count >= 2)

    if supports_dynamic:
        status = "VERIFIERAD"
        label = "Exakt identitet – beslutsstarkt stöd"
        score = min(100, round(70 + (identity_score - 78) * 0.8 + min(source_count, 3) * 5))
    elif supports_exact:
        status = "SÖKBAR"
        label = "Exakt identitet – comp-sökning tillåten, maxbud låst"
        score = min(89, round(60 + (identity_score - 78) * 0.8 + min(source_count, 2) * 4))
    elif critical_complete and conflict_free:
        status = "GRANSKA"
        label = "Nästan komplett identitet – verifiera mer först"
        score = min(77, round(max(35, identity_score * 0.75)))
    else:
        status = "LÅST"
        label = "Exakt identitet låst"
        score = min(59, round(max(0, identity_score * 0.6)))

    if supports_exact:
        exact_requirements = [
            "spelare måste matcha",
            "set/program måste matcha",
            "säsong/år måste matcha",
            "kortnummer måste matcha",
        ]
        if parallel:
            exact_requirements.append(f"parallel/variant måste vara {parallel}")
        if serial not in (None, ""):
            exact_requirements.append(f"serienämnare/numrering måste matcha {serial}")
        if grading_company or grade:
            exact_requirements.append("gradering och graderingsbolag måste matcha")
    else:
        exact_requirements = []

    identity_fields = {
        "player_name": player or None,
        "set_name": set_name or None,
        "season": season or None,
        "card_number": card_number or None,
        "parallel": parallel or None,
        "serial_denominator": serial if serial not in (None, "") else None,
        "grading_company": grading_company or None,
        "grade": grade or None,
        "is_rookie": bool(d.get("is_rookie")),
        "is_auto": bool(d.get("is_auto")),
        "is_patch": bool(d.get("is_patch") or d.get("is_jersey")),
    }

    return {
        "status": status,
        "label": label,
        "score": int(max(0, min(100, score))),
        "identity_score": round(identity_score),
        "source_count": source_count,
        "missing_fields": missing,
        "blockers": blockers,
        "warnings": warnings,
        "strengths": strengths,
        "conflicts": conflicts,
        "supports_exact_comp_search": supports_exact,
        "supports_dynamic_max_bid": supports_dynamic,
        "identity_fields": identity_fields,
        "exact_comp_requirements": exact_requirements,
        "safe_for_valuation": False,
        "note": (
            "Exact Identity Gate värderar inte kortet. Den avgör bara om identiteten "
            "är tillräckligt komplett och konsekvent för exakta comps och, på striktare nivå, "
            "ett comp-stött dynamiskt maxbud."
        ),
    }
