from __future__ import annotations

from typing import Any


CATEGORY_LABELS = {
    "rookie_program": "Rookieprogram",
    "rookie_parallel": "Rookieparallel",
    "rookie_auto": "Rookieautograf",
    "rookie_patch_auto": "Rookie patch-auto",
    "parallel": "Parallel",
    "parallel_family": "Parallelfamilj",
    "ssp_insert": "SSP/chase-insert",
    "insert": "Insert",
    "autograph_program": "Autografprogram",
    "autograph_parallel": "Autografparallel",
    "memorabilia": "Memorabilia/patch",
    "autograph_relic": "Autograf + relic/patch",
    "book_card": "Book card",
    "grail_program": "Grail-program",
    "case_hit": "Case-hit",
}


def _importance_reason(signal: dict[str, Any]) -> str:
    if signal.get("importance_reason"):
        return str(signal["importance_reason"])

    label = str(signal.get("label") or "Kortstrukturen")
    category = str(signal.get("category") or "")
    print_run = signal.get("print_run")

    if print_run == 1:
        return f"{label} är dokumenterad som 1/1-struktur och måste därför identifieras exakt innan den jämförs med andra varianter."
    if isinstance(print_run, int) and print_run <= 10:
        return f"{label} har mycket låg dokumenterad upplaga (/{print_run}); fel parallel kan därför ge helt fel comps."
    if isinstance(print_run, int) and print_run <= 25:
        return f"{label} är en lågnumrerad variant (/{print_run}) där exakt parallel och serial är avgörande för jämförbarheten."
    if isinstance(print_run, int) and print_run <= 100:
        return f"{label} är en numrerad premiumvariant (/{print_run}); samma spelare i basversionen är inte en tillräcklig jämförelse."
    if "rookie" in category and "auto" in category:
        return f"{label} kombinerar rookie-status med autograf/patch-struktur och bör därför behandlas som ett separat kortprogram i comp-sökningen."
    if category == "rookie_program":
        return f"{label} är ett etablerat rookieprogram. Det är viktigare att identifiera programmet korrekt än att bara konstatera att kortet är ett rookie-kort."
    if category == "ssp_insert":
        return f"{label} är ett dokumenterat chase/SSP-program och ska inte värderas som ett vanligt bas- eller insertkort."
    if category in {"parallel", "rookie_parallel", "parallel_family"}:
        return f"{label} är en särskild parallelstruktur. Exakt variant behöver verifieras innan prisjämförelser används."
    if "autograph" in category:
        return f"{label} är ett särskilt autografprogram och bör jämföras mot samma autografserie, inte mot vanliga kort från produkten."
    if category == "memorabilia":
        return f"{label} är ett separat memorabilia/patch-program; materialtyp och numrering behöver matcha comps."
    return f"{label} är en känd samlarstruktur som förtjänar extra kontroll av exakt kortidentitet och comps."


def _verify_reason(signal: dict[str, Any]) -> str:
    category = str(signal.get("category") or "")
    print_run = signal.get("print_run")
    checks = []
    if "rookie" in category:
        checks.append("rookieprogram")
    if category in {"parallel", "rookie_parallel", "parallel_family", "autograph_parallel"}:
        checks.append("parallel")
    if isinstance(print_run, int):
        checks.append(f"serial /{print_run}")
    if "autograph" in category or "auto" in category:
        checks.append("autograf")
    if "patch" in category or category == "memorabilia":
        checks.append("patch/materialtyp")
    if category in {"ssp_insert", "insert"}:
        checks.append("insertnamn")
    checks.extend(["säsong", "kortnummer"])
    # stable order, no duplicates
    unique = []
    for value in checks:
        if value not in unique:
            unique.append(value)
    return "Verifiera " + ", ".join(unique[:5]) + " innan exact comps används."


def _tier(signal: dict[str, Any]) -> int:
    explicit = signal.get("knowledge_tier")
    if isinstance(explicit, int):
        return max(1, min(5, explicit))
    priority = int(signal.get("attention_priority", 0) or 0)
    print_run = signal.get("print_run")
    if print_run == 1:
        return 5
    if isinstance(print_run, int) and print_run <= 10:
        return 5
    if isinstance(print_run, int) and print_run <= 25:
        return max(4, priority)
    return max(1, min(5, priority or 2))


def build_card_intelligence(signals: list[dict] | None, features: dict | None = None) -> dict:
    """Translate known product/checklist signals into collector-facing context.

    The output is descriptive knowledge only. It never estimates a price and must
    not be used to create resale values, profit, max bids or buy decisions.
    """
    signals = [dict(s) for s in (signals or []) if isinstance(s, dict)]
    features = dict(features or {})
    if not signals:
        return {
            "level": "Ingen känd struktur",
            "tier": 0,
            "summary": "Ingen särskild kortstruktur i kunskapsbanken matchade annonsen.",
            "paths": [],
            "reasons": [],
            "verification_steps": [],
            "source_ids": [],
        }

    enriched = []
    for signal in signals:
        tier = _tier(signal)
        category = str(signal.get("category") or "unknown")
        enriched.append({
            **signal,
            "knowledge_tier": tier,
            "category_label": CATEGORY_LABELS.get(category, category.replace("_", " ").title()),
            "importance_reason": _importance_reason(signal),
            "verification_step": _verify_reason(signal),
            "product_family": signal.get("product_family"),
            "program_family": signal.get("program_family") or signal.get("label"),
        })

    enriched.sort(key=lambda s: (int(s.get("knowledge_tier", 0)), int(s.get("attention_priority", 0) or 0)), reverse=True)
    top_tier = int(enriched[0].get("knowledge_tier", 0))
    level = {
        5: "Mycket viktig kortstruktur",
        4: "Viktig kortstruktur",
        3: "Förhöjd samlarbetydelse",
        2: "Känd kortstruktur",
        1: "Grundsignal",
    }.get(top_tier, "Känd kortstruktur")

    paths = []
    for signal in enriched[:4]:
        parts = []
        if signal.get("product_family"):
            parts.append(str(signal["product_family"]))
        if signal.get("program_family"):
            parts.append(str(signal["program_family"]))
        if signal.get("print_run"):
            parts.append(f"/{signal['print_run']}")
        paths.append(" → ".join(parts) if parts else str(signal.get("label") or "Okänd struktur"))

    reasons = []
    verification = []
    source_ids = []
    for signal in enriched[:4]:
        for value, target in [
            (signal.get("importance_reason"), reasons),
            (signal.get("verification_step"), verification),
            (signal.get("source_id"), source_ids),
        ]:
            if value and value not in target:
                target.append(value)

    detected_context = []
    if features.get("rookie"):
        detected_context.append("rookie")
    if features.get("autograph"):
        detected_context.append("autograf")
    if features.get("patch") or features.get("relic"):
        detected_context.append("patch/relic")
    if features.get("serial_number") or features.get("serial_denominator"):
        detected_context.append("serial")
    context_text = f" Annonsen innehåller även signaler för {', '.join(detected_context)}." if detected_context else ""

    summary = (
        f"{level}: {enriched[0].get('label', 'känd struktur')}. "
        "Kunskapsbanken används för att förstå vilken korttyp som måste verifieras och vilka comps som är relevanta – inte för att skapa ett pris."
        + context_text
    )
    return {
        "level": level,
        "tier": top_tier,
        "summary": summary,
        "paths": paths,
        "reasons": reasons,
        "verification_steps": verification,
        "source_ids": source_ids,
        "signals": enriched,
    }
