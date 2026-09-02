from __future__ import annotations

from typing import Any


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def _chase_class(signal: dict[str, Any]) -> str:
    category = str(signal.get("category") or "").casefold()
    label = str(signal.get("label") or "").casefold()
    print_run = signal.get("print_run")

    if print_run == 1 or "1/1" in label:
        return "one_of_one"
    if isinstance(print_run, int) and print_run <= 10:
        return "ultra_low_serial"
    if "rookie" in category and ("patch" in category or "auto" in category):
        return "rookie_signature"
    if "rookie" in category:
        return "flagship_rookie"
    if category in {"ssp_insert", "case_hit", "grail_program"}:
        return "ssp_case_hit"
    if "autograph" in category or "auto" in category:
        return "signature_program"
    if category in {"memorabilia", "autograph_relic", "book_card"} or "book" in label:
        return "premium_relic_book"
    if "parallel" in category:
        return "parallel_hierarchy"
    return "collector_program"


def build_chase_knowledge_graph(
    *,
    signals: list[dict[str, Any]] | None,
    player_name: str | None = None,
    player_market_score: int | float | None = None,
    features: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a collector-knowledge graph without inventing monetary value.

    The graph explains *what kind of chase structure* a listing may belong to and
    what must be verified next. It is intentionally prohibited from creating or
    modifying market value, resale estimates, ROI, profit, max bid or buy decisions.
    """
    signals = [dict(s) for s in (signals or []) if isinstance(s, dict)]
    features = dict(features or {})
    player_score = _clamp(float(player_market_score or 0))

    if not signals:
        return {
            "priority_score": 0,
            "level": "Ingen chase-struktur identifierad",
            "profile": "Otillräckligt kunskapsunderlag",
            "nodes": [],
            "edges": [],
            "reasons": [],
            "verification_steps": [],
            "source_ids": [],
            "safe_for_valuation": False,
            "note": "Ingen dokumenterad chase-struktur matchade. Kunskapsgrafen är inte en prisguide.",
        }

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    reasons: list[str] = []
    verify: list[str] = []
    source_ids: list[str] = []
    classes: list[str] = []

    raw_score = 0.0
    strongest_tier = 0
    lowest_run: int | None = None

    for idx, signal in enumerate(signals[:8]):
        label = str(signal.get("label") or f"Signal {idx+1}")
        product = str(signal.get("product_family") or "Okänd produkt")
        program = str(signal.get("program_family") or label)
        category = str(signal.get("category") or "unknown")
        tier = int(signal.get("knowledge_tier") or signal.get("attention_priority") or 1)
        tier = max(1, min(5, tier))
        strongest_tier = max(strongest_tier, tier)
        print_run = signal.get("print_run")
        chase_class = _chase_class(signal)
        classes.append(chase_class)

        if isinstance(print_run, int):
            lowest_run = print_run if lowest_run is None else min(lowest_run, print_run)

        product_id = f"product:{product.casefold()}"
        program_id = f"program:{program.casefold()}"
        variant_id = f"variant:{label.casefold()}"
        existing_ids = {n["id"] for n in nodes}
        if product_id not in existing_ids:
            nodes.append({"id": product_id, "type": "product", "label": product})
        existing_ids = {n["id"] for n in nodes}
        if program_id not in existing_ids:
            nodes.append({"id": program_id, "type": "program", "label": program})
            edges.append({"from": product_id, "to": program_id, "relation": "innehåller"})
        existing_ids = {n["id"] for n in nodes}
        if variant_id not in existing_ids:
            nodes.append({
                "id": variant_id,
                "type": "variant",
                "label": label,
                "category": category,
                "chase_class": chase_class,
                "print_run": print_run,
            })
            if variant_id != program_id:
                edges.append({"from": program_id, "to": variant_id, "relation": "variant/program"})

        raw_score += tier * 9
        if print_run == 1:
            raw_score += 20
        elif isinstance(print_run, int) and print_run <= 10:
            raw_score += 14
        elif isinstance(print_run, int) and print_run <= 25:
            raw_score += 9
        elif isinstance(print_run, int) and print_run <= 100:
            raw_score += 4
        if chase_class in {"ssp_case_hit", "rookie_signature", "premium_relic_book"}:
            raw_score += 6
        if chase_class == "one_of_one":
            raw_score += 15

        source_id = signal.get("source_id")
        if source_id and source_id not in source_ids:
            source_ids.append(str(source_id))

    # Player demand can increase review priority, but can never convert knowledge into value.
    if player_name and player_score >= 90:
        raw_score += 8
        reasons.append(f"Hög spelarefterfrågan ({player_score}/100) gör dokumenterad chase-struktur extra relevant att verifiera.")
    elif player_name and player_score >= 75:
        raw_score += 4
        reasons.append(f"Tydlig spelarefterfrågan ({player_score}/100) stärker granskningsprioriteten, inte värderingen.")
    elif not player_name or player_score <= 0:
        raw_score = min(raw_score, 68)
        reasons.append("Spelaren är inte säkert identifierad; chase-signalen hålls därför konservativ.")

    if features.get("is_lot"):
        raw_score = min(raw_score, 55)
        reasons.append("Annonsen verkar vara en lot; en enskild chase-identitet får inte antas gälla hela annonsen.")
    if not features.get("card_number") and strongest_tier >= 4:
        raw_score = min(raw_score, 82)
        verify.append("Verifiera kortnummer innan exact comps används.")
    if features.get("identity_conflicts"):
        raw_score = min(raw_score, 50)
        reasons.append("Identitetskonflikt finns mellan annonsens bevis; chase-profilen får inte behandlas som bekräftad.")

    if "one_of_one" in classes:
        profile = "1/1 / grail-kandidat – exakt identitet krävs"
        verify.append("Verifiera 1/1-markering, produkt, variant och kortnummer visuellt.")
    elif "ultra_low_serial" in classes:
        profile = "Ultralåg numrering – hög chase-prioritet"
        verify.append("Verifiera serial och exakt parallell innan jämförelser används.")
    elif "rookie_signature" in classes:
        profile = "Rookie-signatur/patch – separat chase-program"
        verify.append("Verifiera rookieprogram, autograf/patch och variant.")
    elif "ssp_case_hit" in classes:
        profile = "SSP/case-hit – chase-program"
        verify.append("Verifiera att insert-/case-hit-namnet faktiskt tillhör rätt produkt och säsong.")
    elif "premium_relic_book" in classes:
        profile = "Premium auto/relic/book – separat samlarprogram"
        verify.append("Verifiera materialtyp, autograf, spelare och eventuell numrering.")
    elif "parallel_hierarchy" in classes:
        profile = "Parallelhierarki – exakt variant avgör jämförbarheten"
        verify.append("Verifiera parallel, färg/finish och serial.")
    else:
        profile = "Dokumenterad chase-/samlarstruktur"

    labels = [str(s.get("label")) for s in signals if s.get("label")]
    if labels:
        reasons.insert(0, "Kunskapsbanken matchar: " + ", ".join(labels[:4]) + ".")
    if lowest_run is not None:
        reasons.append(f"Lägsta dokumenterade upplaga i matchade signaler är /{lowest_run}.")

    score = _clamp(raw_score)
    if score >= 88:
        level = "Grail/chase – verifiera först"
    elif score >= 74:
        level = "Mycket hög chase-prioritet"
    elif score >= 58:
        level = "Hög chase-prioritet"
    elif score >= 40:
        level = "Förhöjd chase-prioritet"
    else:
        level = "Normal chase-prioritet"

    # Stable, deduplicated verification list.
    verification_steps: list[str] = []
    for item in verify + [
        "Matcha säsong och produktfamilj.",
        "Kräv exact sold comps innan kortets chase-status påverkar ett köpbeslut.",
    ]:
        if item not in verification_steps:
            verification_steps.append(item)

    return {
        "priority_score": score,
        "level": level,
        "profile": profile,
        "nodes": nodes,
        "edges": edges,
        "reasons": reasons[:6],
        "verification_steps": verification_steps[:6],
        "source_ids": source_ids,
        "classes": sorted(set(classes)),
        "safe_for_valuation": False,
        "note": (
            "Grail & Chase Knowledge Graph beskriver dokumenterade kortprogram och relationer. "
            "Den får aldrig skapa pris, ROI, vinst, maxbud eller köpbeslut utan marknadsdata."
        ),
    }
