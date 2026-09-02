from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.card_market_knowledge import load_card_market_knowledge


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _program_name(signal: dict[str, Any]) -> str:
    return str(signal.get("program_family") or signal.get("label") or "Okänt program")


def _sort_key(signal: dict[str, Any]) -> tuple:
    run = signal.get("print_run")
    run_order = int(run) if isinstance(run, int) and run > 0 else 10**9
    tier = int(signal.get("knowledge_tier") or signal.get("attention_priority") or 0)
    return (run_order, -tier, str(signal.get("label") or ""))


def build_knowledge_library() -> dict[str, Any]:
    """Build a reusable product -> program -> variant library from verified knowledge data.

    The library is descriptive. It has no prices, multipliers, ROI, profit or bid logic.
    """
    data = load_card_market_knowledge()
    products: dict[str, dict[str, Any]] = {}

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in data.get("signals", []):
        if not isinstance(raw, dict):
            continue
        product = str(raw.get("product_family") or "Okänd produktfamilj")
        grouped[product].append(dict(raw))

    for product, signals in grouped.items():
        programs: dict[str, dict[str, Any]] = {}
        for signal in signals:
            program = _program_name(signal)
            entry = programs.setdefault(program, {
                "name": program,
                "variants": [],
                "categories": [],
                "source_ids": [],
            })
            variant = {
                "label": signal.get("label"),
                "category": signal.get("category"),
                "print_run": signal.get("print_run"),
                "rarity_signal": signal.get("rarity_signal"),
                "knowledge_tier": int(signal.get("knowledge_tier") or signal.get("attention_priority") or 0),
                "source_id": signal.get("source_id"),
            }
            entry["variants"].append(variant)
            if signal.get("category") and signal.get("category") not in entry["categories"]:
                entry["categories"].append(signal.get("category"))
            if signal.get("source_id") and signal.get("source_id") not in entry["source_ids"]:
                entry["source_ids"].append(signal.get("source_id"))

        for program in programs.values():
            program["variants"].sort(key=_sort_key)
            runs = [v["print_run"] for v in program["variants"] if isinstance(v.get("print_run"), int)]
            program["lowest_print_run"] = min(runs) if runs else None
            program["variant_count"] = len(program["variants"])

        products[product] = {
            "name": product,
            "programs": sorted(programs.values(), key=lambda p: p["name"]),
            "program_count": len(programs),
            "variant_count": sum(len(p["variants"]) for p in programs.values()),
        }

    return {
        "version": data.get("version"),
        "product_count": len(products),
        "signal_count": sum(len(v) for v in grouped.values()),
        "products": products,
    }


def explain_library_match(signals: list[dict] | None) -> dict[str, Any]:
    """Explain how matched signals sit inside their known product/program families."""
    matches = [dict(s) for s in (signals or []) if isinstance(s, dict)]
    if not matches:
        return {
            "matched": False,
            "summary": "Ingen match mot Card Knowledge Library.",
            "families": [],
            "comp_boundaries": [],
            "safe_for_valuation": False,
        }

    library = build_knowledge_library()
    families: list[dict[str, Any]] = []
    boundaries: list[str] = []

    seen = set()
    for match in matches[:8]:
        product = str(match.get("product_family") or "Okänd produktfamilj")
        program = _program_name(match)
        label = str(match.get("label") or program)
        key = (_norm(product), _norm(program))
        if key in seen:
            continue
        seen.add(key)

        product_entry = library["products"].get(product, {})
        programs = product_entry.get("programs", [])
        program_entry = next((p for p in programs if _norm(p.get("name")) == _norm(program)), None)

        siblings = []
        if program_entry:
            siblings = [
                {
                    "label": v.get("label"),
                    "print_run": v.get("print_run"),
                    "category": v.get("category"),
                }
                for v in program_entry.get("variants", [])
                if _norm(v.get("label")) != _norm(label)
            ]

        families.append({
            "product_family": product,
            "program_family": program,
            "matched_variant": label,
            "matched_print_run": match.get("print_run"),
            "sibling_variants": siblings[:8],
            "known_variant_count": int(program_entry.get("variant_count", 1)) if program_entry else 1,
            "lowest_known_print_run": program_entry.get("lowest_print_run") if program_entry else match.get("print_run"),
        })

        if siblings:
            boundaries.append(
                f"{label} tillhör familjen {program}; comps från syskonvarianter ska inte behandlas som exakta utan separat identitetsmatchning."
            )
        if isinstance(match.get("print_run"), int):
            boundaries.append(
                f"Matchad variant är dokumenterad /{match['print_run']}; annan serial denominator är en identitetskonflikt, inte en nära comp."
            )

    products = list(dict.fromkeys(f["product_family"] for f in families))
    summary = (
        "Card Knowledge Library placerar matchningen i "
        + ", ".join(products[:3])
        + " och visar relaterade program/varianter för säkrare identifiering."
    )
    return {
        "matched": True,
        "summary": summary,
        "families": families,
        "comp_boundaries": list(dict.fromkeys(boundaries))[:8],
        "library_version": library.get("version"),
        "safe_for_valuation": False,
        "note": "Biblioteket beskriver relationer mellan kortfamiljer. Det får aldrig skapa pris eller maxbud utan marknadsdata.",
    }
