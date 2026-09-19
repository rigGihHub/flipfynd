"""Hard guardrails for Top 5 usefulness.

A Top 5 should contain actionable candidates, not five known negative-margin
rows. When evidence is weak, prefer unknown-but-researchable over known-bad.
"""
from __future__ import annotations

def _n(v, default=None):
    try: return float(v)
    except (TypeError, ValueError): return default

def usefulness(row):
    margin=_n(row.get("practical_margin"))
    source=row.get("practical_price_source")
    potential=_n(row.get("potential"),0) or 0
    roi=_n(row.get("practical_roi"))
    total=_n(row.get("total_cost"))
    sold=int(_n(row.get("sold_comps"),0) or 0)
    asking_count=int(_n(row.get("asking_comparison_count"),0) or 0)
    flags=[]
    if margin is not None and margin < 0: flags.append("KNOWN_NEGATIVE_MARGIN")
    if potential <= 0: flags.append("ZERO_POTENTIAL")
    if source is None: flags.append("NO_PRICE_CONTEXT")
    # 21-30: hard usefulness dimensions for practical flipping.
    if margin is not None and 0 < margin < 20: flags.append("TINY_NOMINAL_MARGIN")
    if roi is not None and roi < 0.15: flags.append("LOW_ROI")
    if total is not None and total >= 500 and source == "MODEL_GUIDE": flags.append("HIGH_CAPITAL_WEAK_EVIDENCE")
    if source == "MODEL_GUIDE" and sold == 0 and asking_count == 0: flags.append("MODEL_ONLY")
    if row.get("generic_lot"): flags.append("GENERIC_LOT")
    if row.get("asking_warning"): flags.append("ASKING_CONTRADICTION")
    if row.get("reality_gate_penalty",0) and float(row.get("reality_gate_penalty") or 0)>=25: flags.append("HIGH_REALITY_PENALTY")
    if row.get("certainty") is not None and float(row.get("certainty") or 0)<20: flags.append("VERY_LOW_CERTAINTY")
    if not row.get("url"): flags.append("NO_LISTING_LINK")
    if potential <= 0 and margin is None: flags.append("NO_ECONOMIC_SIGNAL")

    actionable = margin is None or margin > 0
    quality_penalty = sum({
        "TINY_NOMINAL_MARGIN":4, "LOW_ROI":4, "HIGH_CAPITAL_WEAK_EVIDENCE":12,
        "MODEL_ONLY":5, "GENERIC_LOT":12, "ASKING_CONTRADICTION":10,
        "HIGH_REALITY_PENALTY":8, "VERY_LOW_CERTAINTY":5,
        "NO_LISTING_LINK":8, "NO_ECONOMIC_SIGNAL":6,
    }.get(flag,0) for flag in flags)
    return {
        "actionable": actionable,
        "known_negative": margin is not None and margin < 0,
        "margin": margin,
        "quality_penalty": quality_penalty,
        "flags": flags,
    }

def build_useful_top5(rows, limit=5):
    enriched=[]
    for row in rows or []:
        r=dict(row); r["usefulness"]=usefulness(r); enriched.append(r)
    positive=[r for r in enriched if (r["usefulness"]["margin"] is not None and r["usefulness"]["margin"]>0)]
    unknown=[r for r in enriched if r["usefulness"]["margin"] is None]
    negative=[r for r in enriched if r["usefulness"]["known_negative"]]
    key=lambda r:(
        -float((r.get("usefulness") or {}).get("quality_penalty") or 0),
        float(r.get("potential") or 0),
        float(r.get("certainty") or 0),
        float(r.get("freshness_score") or 0)
    )
    positive.sort(key=lambda r:((_n(r.get("practical_margin"),0) or 0),(_n(r.get("practical_roi"),0) or 0),*key(r)),reverse=True)
    unknown.sort(key=key,reverse=True)
    negative.sort(key=lambda r:((_n(r.get("practical_margin"),-10**9) or -10**9),*key(r)),reverse=True)
    # Never let known losers crowd out researchable unknowns.
    # Product rule: known negative-margin rows are not fynd candidates.
    # Do not pad Top 5 with losers merely to reach five. A shorter useful list
    # is more honest and more actionable than five zero-potential rows.
    final=(positive+unknown)[:limit]

    # Candidate rescue: if strict economics yields too few rows, surface the
    # strongest research candidates whose economics are genuinely unknown.
    # Never rescue a known negative-margin card. This keeps Top 5 useful while
    # making special-engine signals feed the main workflow automatically.
    if len(final) < limit:
        used = {r.get("url") or str(r.get("title") or "").casefold() for r in final}
        rescue = []
        for r in enriched:
            marker = r.get("url") or str(r.get("title") or "").casefold()
            if marker in used or r["usefulness"]["known_negative"]:
                continue
            source = r.get("_source_item") or {}
            research_strength = (
                float(r.get("discovery_score") or 0) + min(18.0, float(source.get("special_engine_strength") or 0))
                + (8 if source.get("is_information_edge_candidate") else 0)
                + (7 if source.get("is_hidden_find_candidate") else 0)
                + (6 if source.get("mispriced_rookie_candidate") else 0)
                + (6 if source.get("misclassified_card_candidate") else 0)
                + min(8, float(source.get("valuable_card_structure_score") or 0))
            )
            if research_strength <= 0:
                continue
            rr = dict(r)
            rr["candidate_rescue"] = True
            rr["rescue_score"] = round(research_strength, 1)
            rescue.append(rr)
        rescue.sort(key=lambda r: (
            float(r.get("rescue_score") or 0),
            float(r.get("certainty") or 0),
            float(r.get("freshness_score") or 0),
        ), reverse=True)
        final.extend(rescue[:limit-len(final)])

    for r in final:
        r["best_of_bad_market"] = bool(r["usefulness"]["known_negative"])
    return final
