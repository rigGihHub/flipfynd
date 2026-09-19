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
    flags=[]
    if margin is not None and margin < 0: flags.append("KNOWN_NEGATIVE_MARGIN")
    if potential <= 0: flags.append("ZERO_POTENTIAL")
    if source is None: flags.append("NO_PRICE_CONTEXT")
    actionable = margin is None or margin > 0
    return {
        "actionable": actionable,
        "known_negative": margin is not None and margin < 0,
        "margin": margin,
        "flags": flags,
    }

def build_useful_top5(rows, limit=5):
    enriched=[]
    for row in rows or []:
        r=dict(row); r["usefulness"]=usefulness(r); enriched.append(r)
    positive=[r for r in enriched if (r["usefulness"]["margin"] is not None and r["usefulness"]["margin"]>0)]
    unknown=[r for r in enriched if r["usefulness"]["margin"] is None]
    negative=[r for r in enriched if r["usefulness"]["known_negative"]]
    key=lambda r:(float(r.get("potential") or 0),float(r.get("certainty") or 0),float(r.get("freshness_score") or 0))
    positive.sort(key=lambda r:((_n(r.get("practical_margin"),0) or 0),(_n(r.get("practical_roi"),0) or 0),*key(r)),reverse=True)
    unknown.sort(key=key,reverse=True)
    negative.sort(key=lambda r:((_n(r.get("practical_margin"),-10**9) or -10**9),*key(r)),reverse=True)
    # Never let known losers crowd out researchable unknowns.
    final=(positive+unknown)[:limit]
    if len(final)<limit:
        final.extend(negative[:limit-len(final)])
    for r in final:
        r["best_of_bad_market"] = bool(r["usefulness"]["known_negative"])
    return final
