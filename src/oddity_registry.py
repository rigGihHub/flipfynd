"""Curated oddity/story-card knowledge base.

The registry is deliberately conservative. A match only creates a research lead.
It never creates a price, exact SOLD comp or BUY decision.
"""
from __future__ import annotations
import re


def _norm(v):
    return re.sub(r"[^a-z0-9]+", " ", str(v or "").casefold()).strip()

# Taxonomy is much broader than the seed-card list so the research engine can
# classify unusual value mechanisms without inventing a premium.
ODDITY_TAXONOMY = {
    "ERROR_CORRECTION": "Feltryck / korrigerad version",
    "IMAGE_VARIATION": "Bildvariant / reverse negative / fel foto",
    "CENSORSHIP": "Censur / ändrad reklam eller text",
    "MISSING_PRINT": "Saknad text / namn / färg / folie",
    "BACKGROUND_STORY": "Ovanlig person eller händelse i bakgrunden",
    "REGIONAL_DISTRIBUTION": "Regional / food issue / team issue",
    "PROMO_TEST": "Promo / sample / prototype / test issue",
    "FACTORY_ONLY": "Factory-set-only / glossy / premium print",
    "CONDITION_RARITY": "Condition rarity / svår hög grade",
    "HISTORIC_IMAGE": "Ikoniskt eller historiskt foto/ögonblick",
    "PROVENANCE": "Proveniens / historisk ägarkedja",
    "CROSSOVER": "Crossover-intresse utanför sporten",
    "MARKET_EVENT": "Efterfrågechock efter dödsfall, rekord, dokumentär m.m.",
    "KEY_CARD": "Master-set / registry-set / nyckelkort",
    "SERIAL_AESTHETIC": "Jersey-number / first-last serial",
}

# Narrow, well-known seeds. These are intentionally not used as valuations.
CURATED_ODDITY_CARDS = [
    dict(key="mark_jackson_menendez_background", sport="basketball", season="1990-91", set_tokens=("hoops",), card_number="205", player_tokens=("mark","jackson"), category="BACKGROUND_STORY", title="Mark Jackson #205 – Menendez brothers in background", research="Verifiera att annonsbilden är rätt 1990-91 Hoops #205 och jämför färska SOLD för story-kortet.", reference_traits=("två män sitter på courtside-raden bakom spelaren", "bakgrundsdetaljen finns i originalfotot och är inte en tryckdefekt"), normal_traits=("samma kortdesign och spelarfoto",)),
    dict(key="randy_johnson_marlboro", sport="baseball", season="1989", set_tokens=("fleer",), card_number="381", player_tokens=("randy","johnson"), category="CENSORSHIP", title="Randy Johnson #381 – Marlboro/censurvarianter", research="Fastställ exakt Marlboro/censurvariant från bild innan comps jämförs.", reference_traits=("reklamskylten bakom spelaren visar olika grad av Marlboro-detalj", "censureringen sitter i bakgrundsreklamen, inte på kortets textfält"), normal_traits=("andra versioner har mer eller mindre bortretuscherad reklam",)),
    dict(key="billy_ripken_error", sport="baseball", season="1989", set_tokens=("fleer",), card_number="616", player_tokens=("billy","ripken"), category="CENSORSHIP", title="Billy Ripken #616 – bat-knob correction variants", research="Identifiera exakt bat-knob-version; flera korrigeringar existerar och värden skiljer sig.", reference_traits=("text/korrigering på slagträets knob", "flera officiellt kända korrigeringsvarianter finns"), normal_traits=("korrigeringen kan vara blackout, scribble eller annan täckning",)),
    dict(key="frank_thomas_nnof", sport="baseball", season="1990", set_tokens=("topps",), card_number="414", player_tokens=("frank","thomas"), category="MISSING_PRINT", title="Frank Thomas #414 – NNOF", research="Verifiera No Name on Front mot etablerade referensbilder; förväxla inte med vanlig #414.", reference_traits=("spelarnamnet saknas på framsidan", "övrig design ska i stort motsvara vanlig #414"), normal_traits=("vanlig version har Frank Thomas namn tryckt på framsidan",)),
    dict(key="dale_murphy_reverse_negative", sport="baseball", season="1989", set_tokens=("upper","deck"), card_number="357", player_tokens=("dale","murphy"), category="IMAGE_VARIATION", title="Dale Murphy #357 – reverse negative variation", research="Kontrollera orientering/foto mot dokumenterade reverse-negative- och korrigerade versioner.", reference_traits=("spelarfotot är horisontellt spegelvänt jämfört med korrigerad version", "uniform/logotyporientering avslöjar spegelvändningen"), normal_traits=("korrigerad version har rättvänd bild",)),
    dict(key="john_littlefield_reverse_negative", sport="baseball", season="1982", set_tokens=("fleer",), card_number="576", player_tokens=("john","littlefield"), category="IMAGE_VARIATION", title="John Littlefield #576 – reverse negative", research="Verifiera reverse-negative kontra korrigerad version från bild och checklistreferens.", reference_traits=("spelarfotot är spegelvänt jämfört med korrigerad version", "detaljer i uniform och bildorientering ska stämma med reverse-negative-referensen"), normal_traits=("korrigerad version har rättvänd bild",)),
]

TOKEN_RULES = [
    (("error","misprint","feltryck","corrected","correction"), "ERROR_CORRECTION"),
    (("reverse negative","wrong photo","photo variation","image variation"), "IMAGE_VARIATION"),
    (("censor","censored","censur","marlboro"), "CENSORSHIP"),
    (("no name","nnof","missing name","missing foil","missing ink"), "MISSING_PRINT"),
    (("background","menendez","cameo"), "BACKGROUND_STORY"),
    (("regional","food issue","team issue"), "REGIONAL_DISTRIBUTION"),
    (("promo","prototype","sample","test issue"), "PROMO_TEST"),
    (("factory set only","tiffany","glossy"), "FACTORY_ONLY"),
]


def match_curated_cards(*, title="", sport="", player_name="", features=None):
    features = dict(features or {})
    parts = [title, player_name, features.get("set_name"), features.get("season"), features.get("year"), features.get("card_number"), features.get("parallel"), features.get("variant")]
    hay = _norm(" ".join(str(x) for x in parts if x not in (None, "")))
    sport_n = _norm(sport)
    season = _norm(features.get("season") or features.get("year"))
    set_n = _norm(features.get("set_name"))
    num = re.sub(r"^#", "", str(features.get("card_number") or "").strip())
    player_n = _norm(player_name or features.get("player_name"))
    matches = []
    for row in CURATED_ODDITY_CARDS:
        if row["sport"] and row["sport"] not in sport_n:
            continue
        if row["season"] and _norm(row["season"]) not in season and _norm(row["season"]) not in hay:
            continue
        if row["card_number"] and row["card_number"] != num and f" {row['card_number']} " not in f" {hay} ":
            continue
        if not all(tok in (set_n or hay) for tok in row["set_tokens"]):
            continue
        if " ".join(row["player_tokens"]) not in (player_n or hay):
            continue
        matches.append(dict(row))
    return matches


def classify_listing_text(text):
    hay = _norm(text)
    found=[]
    for tokens, category in TOKEN_RULES:
        if any(_norm(tok) in hay for tok in tokens):
            found.append(category)
    return list(dict.fromkeys(found))


def registry_stats():
    cats={}
    for row in CURATED_ODDITY_CARDS:
        cats[row["category"]]=cats.get(row["category"],0)+1
    return {"seed_cards":len(CURATED_ODDITY_CARDS), "taxonomy_categories":len(ODDITY_TAXONOMY), "categories":cats}
