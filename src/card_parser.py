import re
from typing import Optional


KNOWN_PLAYERS = [
    "connor bedard",
    "macklin celebrini",
    "ivan demidov",
    "ryan leonard",
    "connor mcdavid",
    "wayne gretzky",
    "sidney crosby",
    "nathan mackinnon",
    "alex ovechkin",
    "elias pettersson",
    "mats sundin",
    "peter forsberg",
    "juraj slafkovsky",
    "auston matthews",
    "cale makar",
    "igor shesterkin",
    "carey price",
    "jaromir jagr",
    "teemu selanne",
    "nikita kucherov",
    "david pastrnak",
    "leon draisaitl",
    "adam fantilli",
    "lane hutson",
    "matthew knies",
    "quinn hughes",
    "roman josi",
    "martin brodeur",
    "mario lemieux",
    "jarome iginla",
    "joe sakic",
    "mikko rantanen",
    "mitch marner",
    "william nylander",
    "nicklas backstrom",
    "rasmus dahlin",
    "jake sanderson",
    "artem levshunov",
]


SET_PATTERNS = [
    ("the cup", "The Cup"),
    ("sp authentic", "SP Authentic"),
    ("ultimate collection", "Ultimate Collection"),
    ("ultimate", "Ultimate Collection"),
    ("dominion", "Dominion"),
    ("premier", "Premier"),
    ("credentials", "Credentials"),
    ("engrained", "Engrained"),
    ("allure", "Allure"),
    ("stature", "Stature"),
    ("young guns", "Young Guns"),
    ("canvas", "Canvas"),
    ("opc platinum", "OPC Platinum"),
    ("o pee chee platinum", "OPC Platinum"),
    ("o-pee-chee platinum", "OPC Platinum"),
    ("o pee chee", "O-Pee-Chee"),
    ("o-pee-chee", "O-Pee-Chee"),
    ("parkhurst", "Parkhurst"),
    ("artifacts", "Artifacts"),
    ("black diamond", "Black Diamond"),
    ("ice", "Ice"),
    ("mvp", "MVP"),
    ("trilogy", "Trilogy"),
    ("sp game used", "SP Game Used"),
    ("spa", "SP Authentic"),
    ("upper deck", "Upper Deck"),
]


CARD_STOPWORDS = {
    "upper",
    "deck",
    "ud",
    "opc",
    "o",
    "pee",
    "chee",
    "the",
    "cup",
    "sp",
    "authentic",
    "allure",
    "canvas",
    "rookie",
    "young",
    "guns",
    "series",
    "hockey",
    "kort",
    "card",
    "cards",
    "auto",
    "autograph",
    "autograf",
    "patch",
    "jersey",
    "mint",
    "condition",
    "parallel",
    "blue",
    "red",
    "green",
    "gold",
    "silver",
    "violet",
    "retro",
    "future",
    "watch",
    "stature",
    "engrained",
    "credentials",
    "premier",
    "portraits",
    "portrait",
    "team",
    "canada",
    "leaf",
    "parkhurst",
    "score",
    "fleer",
    "insert",
    "prizm",
    "numbered",
    "world",
    "tour",
    "ice",
    "platinum",
    "mvp",
    "edition",
    "retail",
    "hobby",
    "blaster",
    "exclusive",
    "psa",
    "bgs",
    "sgc",
    "lot",
    "collection",
    "samling",
}


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = str(text).lower()
    text = text.replace("\u00a0", " ").replace("\u202f", " ")
    text = re.sub(r"[/]", " / ", text)
    text = re.sub(r"[\(\)\[\]#,.:;!?]", " ", text)
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_player_name(title: str) -> Optional[str]:
    norm = normalize_text(title)

    for player in KNOWN_PLAYERS:
        if player in norm:
            return player.title()

    tokens = norm.split()
    candidates = []

    for token in tokens:
        if token in CARD_STOPWORDS:
            continue
        if re.search(r"\d", token):
            continue
        if len(token) <= 1:
            continue
        if not re.fullmatch(r"[a-zåäö'`]+", token):
            continue
        candidates.append(token)

    if len(candidates) >= 2:
        return f"{candidates[0].title()} {candidates[1].title()}"

    return None


def extract_set_name(title: str) -> Optional[str]:
    norm = normalize_text(title)

    for raw_pattern, display_name in SET_PATTERNS:
        if raw_pattern in norm:
            return display_name

    if re.search(r"\bud\s+young\s+guns\b", norm):
        return "Young Guns"

    return None


def extract_year(title: str) -> Optional[int]:
    norm = normalize_text(title)
    match = re.search(r"\b(19|20)\d{2}\b", norm)
    if match:
        return int(match.group(0))
    return None


def extract_serial_number(title: str) -> Optional[int]:
    raw = str(title or "")
    norm = normalize_text(raw)

    if "1/1" in raw.lower() or "1 1" in norm:
        return 1

    match = re.search(r"/(\d{1,4})\b", raw)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None

    return None


def extract_grade(title: str) -> Optional[str]:
    norm = normalize_text(title)

    grade_patterns = [
        r"\bpsa\s*(10|9|8|7|6)\b",
        r"\bbgs\s*(10|9\.5|9|8\.5|8)\b",
        r"\bsgc\s*(10|9|8)\b",
    ]

    for pattern in grade_patterns:
        match = re.search(pattern, norm)
        if match:
            return match.group(0).upper()

    return None


def detect_parallel(norm: str) -> Optional[str]:
    patterns = [
        "gold",
        "red",
        "blue",
        "green",
        "rainbow",
        "pink",
        "purple",
        "orange",
        "silver",
        "retro",
        "exclusive",
        "speckle",
        "outburst",
        "high gloss",
    ]

    for pattern in patterns:
        if re.search(rf"\b{re.escape(pattern)}\b", norm):
            return pattern.title()

    return None


def parse_card_features(title: str) -> dict:
    norm = normalize_text(title)
    serial_number = extract_serial_number(title)
    set_name = extract_set_name(title)
    player_name = extract_player_name(title)
    grade = extract_grade(title)

    is_rookie = bool(re.search(r"\brookie\b|\brc\b", norm))
    is_auto = bool(re.search(r"\bauto\b|\bautograph\b|\bautograf\b|\bsigned\b|\bsignature\b", norm))
    is_patch = "patch" in norm
    is_jersey = "jersey" in norm or "memorabilia" in norm
    is_game_worn = "game worn" in norm or "game-used" in norm or "game used" in norm
    is_graded = grade is not None or any(x in norm for x in ["psa", "bgs", "sgc"])
    is_lot = "samling" in norm or "lot" in norm or "collection" in norm

    return {
        "normalized_title": norm,
        "player_name": player_name,
        "set_name": set_name,
        "year": extract_year(title),
        "parallel": detect_parallel(norm),
        "is_rookie": is_rookie,
        "is_auto": is_auto,
        "is_patch": is_patch,
        "is_jersey": is_jersey,
        "is_game_worn": is_game_worn,
        "is_graded": is_graded,
        "grade": grade,
        "is_lot": is_lot,
        "serial_number": serial_number,
        "is_low_serial": serial_number is not None and serial_number <= 50,
        "is_mid_serial": serial_number is not None and 51 <= serial_number <= 199,
        "is_high_serial": serial_number is not None and serial_number >= 200,
        "is_1of1": serial_number == 1,
    }