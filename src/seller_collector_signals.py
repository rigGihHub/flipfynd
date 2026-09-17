"""Title-level collector signals used only to prioritize seller inventory research.

These signals never create a BUY decision and never count as SOLD evidence. They
help surface listings whose wording suggests card-specific value drivers so the
normal analyser can inspect them before ordinary base cards.
"""
from __future__ import annotations

import re

from src.card_parser import has_relic_material_evidence
from src.sports_card_signal_knowledge import match_sports_card_signals

_FALSE_AUTO = re.compile(r"\b(signature\s*style|silver\s*script|facsimile|facsimile\s*signature|printed\s*signature|pre[- ]?printed\s*signature)\b", re.I)


def _has_serial_numbering(text: str) -> bool:
    if "numbered" in text or "numrerad" in text: return True
    serial_text=re.sub(r"\b(?:19|20)\d{2}\s*[-/]\s*(?:(?:19|20)?\d{2})\b"," ",text)
    serial_text=re.sub(r"(?<!\d)(\d{2})\s*[-/]\s*(\d{2})(?!\d)",lambda m:" " if (int(m.group(2))-int(m.group(1)))%100==1 else m.group(0),serial_text)
    pattern=re.compile(r"(?<![#\d])(\d{1,4})\s*/\s*(5|10|15|20|25|49|50|75|99|100|199|299|499)\b")
    for match in pattern.finditer(serial_text):
        numerator,denominator=int(match.group(1)),int(match.group(2))
        if denominator==numerator+1 and (numerator>=19 or numerator>=1900): continue
        return True
    return False


def collector_signals(item: dict) -> dict:
    title=str(item.get("titel") or item.get("title") or "").strip(); text=title.casefold(); signals=[]; knowledge_matches=match_sports_card_signals(title)
    def add(name,weight,condition):
        if condition: signals.append((name,weight))
    add("one_of_one",24,bool(re.search(r"(?:\b1\s*/\s*1\b|\bone[- ]of[- ]one\b)",text)))
    add("serial_numbered",18,_has_serial_numbering(text))
    explicit_auto=bool(re.search(r"\b(?:autograph(?:ed)?|auto|on[- ]card\s+auto|hard[- ]signed)\b",text)); add("autograph",17,explicit_auto and not _FALSE_AUTO.search(text))
    add("patch_relic",15,has_relic_material_evidence(text)); add("case_hit_ssp",17,bool(re.search(r"\b(?:ssp|super\s+short\s+print|case\s+hit)\b",text))); add("premium_insert",15,bool(re.search(r"\b(?:downtown|kaboom|color\s+blast|colour\s+blast|stained\s+glass|blank\s+slate)\b",text)))
    # Generic RC/rookie wording is common and not price evidence. Give it only
    # a small discovery nudge; genuinely important rookie structures are added
    # separately by the knowledge matcher (Young Guns, Future Watch etc.).
    add("rookie",4,bool(re.search(r"\b(?:rookie|rc)\b",text)))
    add("rookie_structure",11,bool(re.search(r"\b(?:young\s+guns?|future\s+watch)\b",text)))
    add("premium_parallel",11,bool(re.search(r"\b(?:parallel|refractor|prizm|x-fractor|atomic|gold\s+vinyl|cracked\s+ice|red\s+outburst|exclusives?)\b",text))); add("error_variation",14,bool(re.search(r"\b(?:error|misprint|printing\s+error|variation|variant|wrong\s+back|blank\s+back)\b",text))); add("short_print",10,bool(re.search(r"\bshort\s+print\b",text))); add("printing_plate",20,bool(re.search(r"\b(?:printing|tryck)\s+plate\b",text))); add("buyback",16,bool(re.search(r"\bbuyback\b",text))); add("photo_variation",14,bool(re.search(r"\b(?:photo|image|bild)\s+variation\b",text))); add("acetate",10,bool(re.search(r"\bacetate\b",text))); add("die_cut",8,bool(re.search(r"\bdie[- ]?cut\b",text)))
    for match in knowledge_matches: add(match["name"],int(match["weight"]),True)
    penalty=-14 if re.search(r"\b(?:base\s+card|basekort|common|bas\s*kort)\b",text) else 0
    raw=sum(weight for _,weight in signals)+penalty; score=max(0,min(40,raw))
    return {"score":score,"signals":[name for name,_ in signals],"penalty":penalty,"title":title,"knowledge_matches":knowledge_matches,"verify_first":list(dict.fromkeys(match["verify"] for match in knowledge_matches))}
