"""Conservative purchase-safety interpretation of visual findings."""
from __future__ import annotations


def assess_visual_purchase_safety(findings: dict, comparison: dict | None = None) -> dict:
    findings = findings or {}
    comparison = comparison or {}
    blockers = list(comparison.get("conflicts") or [])
    warnings = []
    overall = float(findings.get("overall_confidence") or 0)
    identity = float(findings.get("identity_confidence") or 0)

    if findings.get("possible_tampering") == "yes":
        blockers.append("möjlig manipulation av kort eller graderingshållare")
    if findings.get("photo_quality") == "poor":
        blockers.append("bildkvaliteten är för låg för köpbeslut")
    if findings.get("back_visible") != "yes":
        warnings.append("kortets baksida saknas")
    elif findings.get("back_text_readable") != "yes":
        warnings.append("texten på baksidan går inte att läsa")
    if findings.get("autograph_visible") == "yes" and findings.get("autograph_type") in {"printed_or_facsimile", "unclear", "unknown"}:
        blockers.append("synlig signatur är inte verifierad som äkta autograf")
    if findings.get("grading_company") and not findings.get("slab_cert_number"):
        warnings.append("graderingsetikett syns men certifikatnumret är inte läsbart")
    if findings.get("needs_closeup"):
        warnings.append("närbild krävs")
    if overall < 0.70 or identity < 0.70:
        blockers.append("bildanalysens säkerhet är för låg")

    blockers = list(dict.fromkeys(str(x) for x in blockers if x))
    warnings = list(dict.fromkeys(warnings))
    safe = not blockers and findings.get("front_visible") == "yes" and findings.get("back_visible") == "yes"
    return {
        "safe_for_purchase_review": safe,
        "status": "BILDERNA STÖDJER FORTSATT KÖPKONTROLL" if safe else "STOPPA KÖP – BILDUNDERLAGET RÄCKER INTE",
        "blockers": blockers,
        "warnings": warnings,
        "note": "Bildkontrollen kan stoppa ett köp men kan aldrig ensam bevisa marknadsvärde eller äkthet.",
    }
