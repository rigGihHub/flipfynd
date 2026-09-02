from __future__ import annotations

from typing import Any


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _serial_rung(print_run: Any) -> tuple[int, str]:
    """Return a descriptive scarcity rung from a documented denominator.

    The rung is structural only. It is never a price multiplier.
    """
    if not isinstance(print_run, int) or print_run <= 0:
        return 0, "Ingen dokumenterad upplaga"
    if print_run == 1:
        return 6, "1/1"
    if print_run <= 5:
        return 5, f"Mycket låg numrering /{print_run}"
    if print_run <= 10:
        return 5, f"Låg numrering /{print_run}"
    if print_run <= 25:
        return 4, f"Låg numrering /{print_run}"
    if print_run <= 50:
        return 4, f"Numrerad /{print_run}"
    if print_run <= 100:
        return 3, f"Numrerad /{print_run}"
    return 2, f"Numrerad /{print_run}"


def _category_rung(category: str, rarity_signal: str) -> tuple[int, str]:
    category_n = _norm(category)
    rarity_n = _norm(rarity_signal)

    if "one_of_one" in rarity_n or "1/1" in rarity_n:
        return 6, "1/1 / grail-nivå i strukturen"
    if category_n in {"grail_program", "case_hit"}:
        return 5, "Grail/case-hit-program"
    if category_n == "ssp_insert" or "ultra_rare" in rarity_n or "case_level" in rarity_n:
        return 4, "SSP / case-level chase"
    if category_n in {"rookie_patch_auto", "autograph_relic", "book_card"}:
        return 4, "Premium auto/relic-struktur"
    if category_n in {"rookie_auto", "autograph_parallel", "autograph_program"}:
        return 3, "Autografprogram"
    if category_n in {"rookie_parallel", "parallel"}:
        return 2, "Parallel"
    if category_n in {"rookie_program", "insert", "memorabilia"}:
        return 1, "Program/insert"
    return 0, "Bas/oklassificerad struktur"


def _rookie_rung(category: str, label: str, rarity_signal: str) -> tuple[int, str]:
    category_n = _norm(category)
    text = f"{_norm(label)} {_norm(rarity_signal)}"

    if category_n == "rookie_patch_auto" or ("rookie" in text and "patch" in text and "auto" in text):
        return 5, "Rookie Patch Auto"
    if category_n == "rookie_auto" or ("rookie" in text and "auto" in text):
        return 4, "Rookie Autograph"
    if category_n == "rookie_parallel":
        return 3, "Rookie Parallel"
    if category_n == "rookie_program" or "flagship_rookie" in text or "rookie" in text:
        return 2, "Rookie Program"
    return 0, "Ingen dokumenterad rookiehierarki"


def build_variant_hierarchy(signals: list[dict] | None, features: dict | None = None) -> dict[str, Any]:
    """Describe structural position inside known card/rookie hierarchies.

    This engine is intentionally non-valuing: no market value, ROI, profit or bid
    ceiling may be created from a ladder position alone.
    """
    features = features or {}
    matches = [dict(s) for s in (signals or []) if isinstance(s, dict)]
    if not matches:
        return {
            "matched": False,
            "variant_rung": 0,
            "variant_label": "Ingen känd variantstege",
            "rookie_rung": 0,
            "rookie_label": "Ingen dokumenterad rookiehierarki",
            "summary": "Ingen säker placering i Variant Ladder & Rookie Hierarchy.",
            "reasons": [],
            "verification_steps": [],
            "safe_for_valuation": False,
        }

    best_variant = (0, "Ingen känd variantstege")
    best_rookie = (0, "Ingen dokumenterad rookiehierarki")
    reasons: list[str] = []
    verification: list[str] = []
    paths: list[str] = []

    for signal in matches[:10]:
        label = str(signal.get("label") or "Okänd variant")
        product = str(signal.get("product_family") or "Okänd produktfamilj")
        program = str(signal.get("program_family") or label)
        print_run = signal.get("print_run")
        category = str(signal.get("category") or "")
        rarity = str(signal.get("rarity_signal") or "")

        serial_rung = _serial_rung(print_run)
        category_rung = _category_rung(category, rarity)
        variant = serial_rung if serial_rung[0] >= category_rung[0] else category_rung
        rookie = _rookie_rung(category, label, rarity)

        if variant[0] > best_variant[0]:
            best_variant = variant
        if rookie[0] > best_rookie[0]:
            best_rookie = rookie

        path = f"{product} → {program} → {label}"
        if isinstance(print_run, int):
            path += f" /{print_run}"
        paths.append(path)

        if isinstance(print_run, int):
            reasons.append(f"{label} har dokumenterad upplaga /{print_run}; denominator måste matcha för exakt comp.")
        elif variant[0] >= 4:
            reasons.append(f"{label} är dokumenterad som {variant[1].lower()}, men utan säkert prisstöd i kunskapsbanken.")
        if rookie[0] >= 2:
            reasons.append(f"{label} placeras på rookie-nivån: {rookie[1]}.")

    # Listing evidence may confirm serial denominator, but must never invent it.
    listed_denominator = features.get("serial_denominator")
    if isinstance(listed_denominator, int) and listed_denominator > 0:
        verification.append(f"Verifiera att kortets synliga/angivna serienummer verkligen är /{listed_denominator}.")
    else:
        if best_variant[0] >= 3:
            verification.append("Verifiera serienumrering eller checklistvariant innan nära/exakta comps används.")

    if best_rookie[0] >= 2:
        verification.append("Verifiera att rookieprogrammet och varianten är samma på jämförelseobjektet – inte bara samma spelare och år.")
    if best_variant[0] >= 4:
        verification.append("Använd inte bas- eller syskonvariant som exakt comp för en SSP/lågnumrerad variant.")

    summary = f"Variantstege {best_variant[0]}/6: {best_variant[1]}."
    if best_rookie[0]:
        summary += f" Rookiehierarki {best_rookie[0]}/5: {best_rookie[1]}."
    summary += " Nivåerna beskriver kortstruktur, inte pris."

    return {
        "matched": True,
        "variant_rung": best_variant[0],
        "variant_label": best_variant[1],
        "rookie_rung": best_rookie[0],
        "rookie_label": best_rookie[1],
        "summary": summary,
        "paths": list(dict.fromkeys(paths))[:8],
        "reasons": list(dict.fromkeys(reasons))[:8],
        "verification_steps": list(dict.fromkeys(verification))[:6],
        "safe_for_valuation": False,
        "note": "Variant- och rookiehierarkin är identitets-/kunskapsstöd. Den får aldrig ensam skapa marknadsvärde, vinst, ROI eller maxbud.",
    }
