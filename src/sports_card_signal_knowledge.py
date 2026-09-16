"""Conservative cross-sport card signal taxonomy.

Named programs are discovery clues, not proof of rarity or value. Every match
must still be verified against the exact year/product checklist and card image.
"""
from __future__ import annotations

import re


SIGNAL_FAMILIES = (
    {
        "name": "football_named_chase",
        "weight": 18,
        "all_patterns": (
            re.compile(r"\b(?:topps|uefa|ucl|ucc|premier\s+league)\b", re.I),
            re.compile(
                r"\b(?:helix|chrome\s+anime|european\s+tour|"
                r"(?:berlin|munich|budapest)\s+at\s+night|triple\s+platinum|"
                r"locked\s+in|ultra[- ]violet|veni\s+vidi\s+vici|"
                r"radiating\s+rookies|mindgame|hype|mojo)\b",
                re.I,
            ),
        ),
        "verify": "exakt fotbollsinsert, år, produkt och odds/checklista mot officiell Topps-dokumentation",
    },
    {
        "name": "flagship_rookie_variant",
        "weight": 16,
        "all_patterns": (
            re.compile(r"\byoung\s+guns?\b", re.I),
            re.compile(
                r"\b(?:ud\s+canvas|canvas|exclusives?|high\s+gloss|clear\s+cut|"
                r"outburst(?:\s+(?:silver|red|gold))?|retro)\b",
                re.I,
            ),
        ),
        "verify": "Young Guns-program, variant, kortnummer och eventuell serialisering mot officiell Upper Deck-checklista",
    },
    {
        "name": "upper_deck_day_with_cup",
        "weight": 18,
        "pattern": re.compile(r"\bday\s+with\s+(?:the\s+)?cup(?:\s+flashbacks?)?\b", re.I),
        "verify": "Day With The Cup-program, år, DC-kortnummer och spelare mot officiell Upper Deck-checklista",
    },
    {
        "name": "upper_deck_population_count",
        "weight": 18,
        "pattern": re.compile(
            r"\bpopulation\s+count(?:\s+(?:1000|500|100|50|25|10|5|1))?\b",
            re.I,
        ),
        "verify": "Population Count-program, tier, PC-kortnummer, år och spelare mot officiell Upper Deck-checklista",
    },
    {
        "name": "named_chase_insert",
        "weight": 16,
        "pattern": re.compile(
            r"\b(?:manga|genesis|color\s*wheel|colour\s*wheel|night\s*moves|"
            r"home\s*field\s*advantage|downtown|kaboom|color\s*blast|colour\s*blast|"
            r"blank\s*slate|stained\s*glass|aurora|storm\s*chasers?|on\s*campus|"
            r"permit\s+to\s+dominate|golden\s+mirror)\b",
            re.I,
        ),
        "verify": "exakt insertnamn mot officiell checklista för rätt år och produkt",
    },
    {
        "name": "elite_parallel",
        "weight": 16,
        "pattern": re.compile(
            r"\b(?:superfractor|superfraktor|gold\s+vinyl|black\s+finite|nebula|"
            r"frozenfractor|high\s+gloss|clear\s+cut|emerald\s+surge|red\s+wave|"
            r"orange\s+wave|sapphire\s+parallel)\b",
            re.I,
        ),
        "verify": "parallelens namn, färg och eventuell serialisering mot exakt checklista",
    },
    {
        "name": "premium_autograph_structure",
        "weight": 15,
        "pattern": re.compile(
            r"\b(?:rookie\s+patch\s+auto(?:graph)?|\brpa\b|cut\s+signature|"
            r"dual\s+auto(?:graph)?|triple\s+auto(?:graph)?|quad\s+auto(?:graph)?|"
            r"inscription\s+auto(?:graph)?|hard[- ]signed|on[- ]card\s+auto(?:graph)?)\b",
            re.I,
        ),
        "verify": "att signaturen är pack-issued och checklistad, inte eftermarknad eller facsimile",
    },
    {
        "name": "premium_relic_structure",
        "weight": 14,
        "pattern": re.compile(
            r"\b(?:logo\s+patch|shield\s+patch|laundry\s+tag|brand\s+logo|"
            r"nameplate|letterman|button\s+relic|glove\s+relic|cleat\s+relic|"
            r"fight\s+strap|stick\s+relic)\b",
            re.I,
        ),
        "verify": "reliktyp, materialpåstående och checklistad variant från kortets fram-/baksida",
    },
    {
        "name": "premium_issue_variant",
        "weight": 11,
        "pattern": re.compile(
            r"\b(?:topps\s+tiffany|desert\s+shield|o-pee-chee\s+premier|"
            r"stadium\s+club\s+first\s+day\s+issue|members?\s+only|"
            r"factory\s+set\s+only|golden\s+mirror)\b",
            re.I,
        ),
        "verify": "distributionsvariantens kännetecken mot dokumenterad referensbild och checklista",
    },
)


def match_sports_card_signals(text: str) -> list[dict]:
    hay = str(text or "")
    matches = []
    for family in SIGNAL_FAMILIES:
        if family.get("all_patterns"):
            found_parts = [pattern.search(hay) for pattern in family["all_patterns"]]
            if not all(found_parts):
                continue
            matched_text = " + ".join(match.group(0) for match in found_parts)
        else:
            found = family["pattern"].search(hay)
            if not found:
                continue
            matched_text = found.group(0)
        matches.append({
            "name": family["name"],
            "weight": int(family["weight"]),
            "matched_text": matched_text,
            "verify": family["verify"],
            "research_only": True,
            "creates_value": False,
            "creates_buy": False,
        })
    return matches


__all__ = ["SIGNAL_FAMILIES", "match_sports_card_signals"]
