import re

from src.card_parser import parse_card_features
from src.comments import build_comment
from src.market_analysis import build_market_analysis


HOCKEY_PLAYERS = {
    "Connor Bedard": (100, "elite"),
    "Macklin Celebrini": (98, "elite"),
    "Ivan Demidov": (97, "elite"),
    "Connor McDavid": (96, "elite"),
    "Wayne Gretzky": (94, "elite"),
    "Matthew Schaefer": (94, "elite"),
    "Sidney Crosby": (91, "elite"),
    "Nathan MacKinnon": (91, "elite"),
    "Michael Misa": (91, "elite"),
    "Nikita Kucherov": (90, "elite"),
    "Leon Draisaitl": (89, "strong"),
    "Cale Makar": (88, "strong"),
    "Zayne Parekh": (88, "strong"),
    "Zeev Buium": (87, "strong"),
    "Auston Matthews": (87, "strong"),
    "Alex Ovechkin": (87, "strong"),
    "Beckett Sennecke": (86, "strong"),
    "Lane Hutson": (86, "strong"),
    "David Pastrnak": (85, "strong"),
    "Porter Martone": (85, "strong"),
    "Ryan Leonard": (84, "strong"),
    "Jimmy Snuggerud": (84, "strong"),
    "Anton Frondell": (83, "strong"),
    "James Hagens": (83, "strong"),
    "Berkly Catton": (82, "strong"),
    "Yaroslav Askarov": (81, "strong"),
    "Sam Dickinson": (80, "strong"),
    "Victor Eklund": (80, "strong"),
    "Artem Levshunov": (79, "strong"),
    "Adam Fantilli": (78, "strong"),
    "Juraj Slafkovsky": (68, "medium"),
    "William Nylander": (66, "medium"),
    "Rasmus Dahlin": (65, "medium"),
    "Elias Pettersson": (62, "medium"),
    "Nils Höglander": (24, "weak"),
    "Nils Hoglander": (24, "weak"),
}


FOOTBALL_PLAYERS = {
    "Lamine Yamal": (100, "elite"),
    "Kylian Mbappé": (98, "elite"),
    "Kylian Mbappe": (98, "elite"),
    "Erling Haaland": (96, "elite"),
    "Jude Bellingham": (95, "elite"),
    "Lionel Messi": (95, "elite"),
    "Cristiano Ronaldo": (94, "elite"),
    "Vinícius Júnior": (93, "elite"),
    "Vinicius Junior": (93, "elite"),
    "Khvicha Kvaratskhelia": (92, "elite"),
    "Désiré Doué": (92, "elite"),
    "Desire Doue": (92, "elite"),
    "Estêvão": (92, "elite"),
    "Estevao": (92, "elite"),
    "Arda Güler": (91, "elite"),
    "Arda Guler": (91, "elite"),
    "Franco Mastantuono": (90, "elite"),
    "Ousmane Dembélé": (90, "elite"),
    "Ousmane Dembele": (90, "elite"),
    "Max Dowman": (90, "elite"),
    "Kenan Yıldız": (89, "strong"),
    "Kenan Yildiz": (89, "strong"),
    "Harry Kane": (89, "strong"),
    "Gilberto Mora": (89, "strong"),
    "Bukayo Saka": (88, "strong"),
    "Lennart Karl": (88, "strong"),
    "Rodri": (87, "strong"),
    "Pedri": (87, "strong"),
    "Michael Olise": (87, "strong"),
    "Pau Cubarsí": (87, "strong"),
    "Pau Cubarsi": (87, "strong"),
    "Raphinha": (86, "strong"),
    "Julián Alvarez": (86, "strong"),
    "Julian Alvarez": (86, "strong"),
    "Nico Williams": (85, "strong"),
    "Rayan Cherki": (85, "strong"),
    "Warren Zaïre-Emery": (84, "strong"),
    "Warren Zaire-Emery": (84, "strong"),
    "Ibrahim Mbaye": (84, "strong"),
    "Ethan Nwaneri": (83, "strong"),
    "Lucas Bergvall": (82, "strong"),
    "Dean Huijsen": (82, "strong"),
    "Kobbie Mainoo": (79, "strong"),
    "Geovany Quenda": (79, "strong"),
    "Jobe Bellingham": (78, "strong"),
    "Ben Doak": (76, "medium"),
    "Quim Junyent": (72, "medium"),
}


HOCKEY_SETS = {
    "Young Guns": 16,
    "The Cup": 18,
    "SP Authentic": 14,
    "Dominion": 10,
    "Ultimate Collection": 10,
    "Premier": 8,
    "Black Diamond": 8,
    "OPC Platinum": 7,
}


FOOTBALL_SETS = {
    "Topps Chrome": 16,
    "Topps Finest": 12,
    "Topps Merlin": 13,
    "Panini Prizm": 15,
    "Panini Select": 12,
    "Topps Museum": 14,
    "Obsidian": 13,
    "Immaculate": 16,
    "National Treasures": 18,
    "Donruss": 8,
}


HOCKEY_PREMIUM = {
    "The Cup",
    "SP Authentic",
    "Dominion",
    "Ultimate Collection",
    "Premier",
    "Black Diamond",
}


FOOTBALL_PREMIUM = {
    "Topps Chrome",
    "Topps Finest",
    "Topps Merlin",
    "Panini Prizm",
    "Panini Select",
    "Topps Museum",
    "Obsidian",
    "Immaculate",
    "National Treasures",
}


def normalize_name(name):
    if not name:
        return None

    aliases = {
        "Connor Mcdavid": "Connor McDavid",
        "Nathan Mackinnon": "Nathan MacKinnon",
        "Kylian Mbappe": "Kylian Mbappé",
        "Vinicius Junior": "Vinícius Júnior",
        "Ousmane Dembele": "Ousmane Dembélé",
        "Arda Guler": "Arda Güler",
        "Desire Doue": "Désiré Doué",
        "Kenan Yildiz": "Kenan Yıldız",
        "Pau Cubarsi": "Pau Cubarsí",
        "Warren Zaire-Emery": "Warren Zaïre-Emery",
    }

    clean = str(
        name
    ).strip()

    return aliases.get(
        clean,
        clean,
    )


def get_player_database(sport):
    if sport == "football":
        return FOOTBALL_PLAYERS

    return HOCKEY_PLAYERS


def detect_known_player(
    title,
    sport,
):
    text = (
        title
        or ""
    ).casefold()

    players = sorted(
        get_player_database(
            sport
        ).keys(),
        key=len,
        reverse=True,
    )

    for player in players:
        if player.casefold() in text:
            return normalize_name(
                player
            )

    return None


def detect_set(
    title,
    sport,
):
    text = (
        title
        or ""
    ).casefold()

    aliases = {
        "Young Guns": [
            "young guns",
            "youngguns",
        ],
        "The Cup": [
            "the cup",
        ],
        "SP Authentic": [
            "sp authentic",
            "future watch",
        ],
        "Dominion": [
            "dominion",
        ],
        "Ultimate Collection": [
            "ultimate collection",
        ],
        "Premier": [
            "premier",
        ],
        "Black Diamond": [
            "black diamond",
        ],
        "OPC Platinum": [
            "opc platinum",
            "o-pee-chee platinum",
        ],
        "Topps Chrome": [
            "topps chrome",
        ],
        "Topps Finest": [
            "topps finest",
            "finest",
        ],
        "Topps Merlin": [
            "topps merlin",
            "merlin chrome",
            "merlin",
        ],
        "Panini Prizm": [
            "panini prizm",
            "prizm",
        ],
        "Panini Select": [
            "panini select",
            "select",
        ],
        "Topps Museum": [
            "topps museum",
            "museum collection",
        ],
        "Obsidian": [
            "obsidian",
        ],
        "Immaculate": [
            "immaculate",
        ],
        "National Treasures": [
            "national treasures",
        ],
        "Donruss": [
            "donruss",
            "optic",
        ],
    }

    available_sets = (
        FOOTBALL_SETS
        if sport == "football"
        else HOCKEY_SETS
    )

    for set_name in available_sets:
        needles = aliases.get(
            set_name,
            [
                set_name.casefold()
            ],
        )

        for needle in needles:
            if needle in text:
                return set_name

    return None


def contains_auto(text):
    return bool(
        re.search(
            r"\b("
            r"auto|"
            r"autograph|"
            r"autograf|"
            r"signed|"
            r"signature"
            r")\b",
            text or "",
            flags=re.IGNORECASE,
        )
    )


def extract_serial(title):
    match = re.search(
        r"(?<!\d)"
        r"(\d{1,4})/"
        r"(\d{1,4})"
        r"(?!\d)",
        title or "",
    )

    if not match:
        return (
            None,
            None,
        )

    return (
        int(match.group(1)),
        int(match.group(2)),
    )


def get_features(
    title,
    sport,
):
    features = dict(
        parse_card_features(
            title
        )
        or {}
    )

    known_player = detect_known_player(
        title,
        sport,
    )

    if known_player:
        features["player_name"] = (
            known_player
        )

    else:
        features["player_name"] = (
            normalize_name(
                features.get(
                    "player_name"
                )
            )
        )

    detected_set = detect_set(
        title,
        sport,
    )

    if detected_set:
        features["set_name"] = (
            detected_set
        )

    _, serial_total = (
        extract_serial(
            title
        )
    )

    text = (
        title
        or ""
    ).lower()

    features["is_rookie"] = bool(
        features.get(
            "is_rookie"
        )
        or re.search(
            r"\b(rookie|rc)\b",
            text,
        )
    )

    features["is_auto"] = bool(
        features.get(
            "is_auto"
        )
        or contains_auto(
            text
        )
    )

    features["is_patch"] = bool(
        features.get(
            "is_patch"
        )
        or "patch" in text
        or "relic" in text
    )

    features["is_jersey"] = bool(
        features.get(
            "is_jersey"
        )
        or "jersey" in text
        or "memorabilia" in text
    )

    features["is_game_worn"] = bool(
        features.get(
            "is_game_worn"
        )
        or "game worn" in text
        or "game-worn" in text
        or "match worn" in text
    )

    features["is_1of1"] = bool(
        features.get(
            "is_1of1"
        )
        or "1/1" in text
    )

    if serial_total is not None:
        features[
            "serial_number"
        ] = serial_total

        features[
            "is_low_serial"
        ] = serial_total <= 50

        features[
            "is_mid_serial"
        ] = (
            51
            <= serial_total
            <= 199
        )

        features[
            "is_high_serial"
        ] = (
            serial_total >= 200
        )

    else:
        features.setdefault(
            "serial_number",
            None,
        )

        features.setdefault(
            "is_low_serial",
            False,
        )

        features.setdefault(
            "is_mid_serial",
            False,
        )

        features.setdefault(
            "is_high_serial",
            False,
        )

    features.setdefault(
        "year",
        None,
    )

    features.setdefault(
        "grade",
        None,
    )

    features.setdefault(
        "parallel",
        None,
    )

    features.setdefault(
        "is_lot",
        (
            "lot" in text
            or "samling" in text
            or "collection" in text
        ),
    )

    return features


def detect_sale_type(item):
    text = (
        item.get(
            "raw_text",
            "",
        )
        or ""
    ).lower()

    if "köp nu" in text:
        return "Köp nu"

    if (
        "utropspris" in text
        or "ledande bud" in text
        or " bud" in text
    ):
        return "Auktion"

    return "Okänd"


def get_player_profile(
    features,
    sport,
):
    player_name = normalize_name(
        features.get(
            "player_name"
        )
    )

    database = get_player_database(
        sport
    )

    if not player_name:
        return {
            "name": None,
            "score": 15,
            "tier": "weak",
        }

    if player_name in database:
        score, tier = (
            database[
                player_name
            ]
        )

        return {
            "name": player_name,
            "score": score,
            "tier": tier,
        }

    score = 45

    if features.get(
        "is_rookie"
    ):
        score += 5

    return {
        "name": player_name,
        "score": min(
            score,
            55,
        ),
        "tier": "medium",
    }


def estimate_title_value(
    item,
    sport,
):
    title = item.get(
        "titel",
        "",
    )

    price = (
        item.get(
            "pris",
            0,
        )
        or 0
    )

    shipping = item.get(
        "frakt"
    )

    shipping = (
        0
        if shipping is None
        else shipping
    )

    total_cost = (
        price
        + shipping
    )

    features = get_features(
        title,
        sport,
    )

    profile = get_player_profile(
        features,
        sport,
    )

    set_name = features.get(
        "set_name"
    )

    sets = (
        FOOTBALL_SETS
        if sport == "football"
        else HOCKEY_SETS
    )

    set_hype = sets.get(
        set_name,
        0,
    )

    value = 8
    confidence = 0.24

    reasons = []
    risks = []

    value += round(
        profile["score"]
        * 0.22
    )

    if profile["score"] >= 85:
        confidence += 0.12

        reasons.append(
            "mycket stark "
            "spelarefterfrågan"
        )

    elif profile["score"] >= 70:
        confidence += 0.07

        reasons.append(
            "stark "
            "spelarefterfrågan"
        )

    elif profile["score"] < 40:
        confidence -= 0.05

        risks.append(
            "svag spelarmarknad"
        )

    if set_hype:
        value += set_hype
        confidence += 0.04

        reasons.append(
            f"starkt set: "
            f"{set_name}"
        )

    if features.get(
        "is_rookie"
    ):
        value += 10
        confidence += 0.04

        reasons.append(
            "rookie/RC"
        )

    if features.get(
        "is_auto"
    ):
        value += 24
        confidence += 0.07

        reasons.append(
            "autograf"
        )

    if (
        features.get(
            "is_patch"
        )
        or features.get(
            "is_jersey"
        )
    ):
        value += 9
        confidence += 0.03

        reasons.append(
            "patch/relic"
        )

    if features.get(
        "is_game_worn"
    ):
        value += 8
        confidence += 0.02

        reasons.append(
            "game/match worn"
        )

    serial = features.get(
        "serial_number"
    )

    if features.get(
        "is_1of1"
    ):
        value += 40
        confidence += 0.08

        reasons.append(
            "1/1"
        )

    elif serial is not None:
        if serial <= 10:
            value += 30

        elif serial <= 25:
            value += 22

        elif serial <= 50:
            value += 15

        elif serial <= 99:
            value += 9

        elif serial <= 199:
            value += 4

        else:
            value += 1

        reasons.append(
            f"numrerat /{serial}"
        )

    if features.get(
        "grade"
    ):
        value += 8
        confidence += 0.03

        reasons.append(
            "graderat"
        )

    if features.get(
        "is_lot"
    ):
        value -= 12
        confidence -= 0.10

        risks.append(
            "samlingsannons"
        )

    premium_sets = (
        FOOTBALL_PREMIUM
        if sport == "football"
        else HOCKEY_PREMIUM
    )

    premium_like = (
        set_name in premium_sets
        or features.get(
            "is_auto"
        )
        or features.get(
            "is_low_serial"
        )
    )

    if (
        premium_like
        and profile["score"] < 55
    ):
        value *= 0.62
        confidence -= 0.08

        risks.append(
            "premium trap"
        )

        reasons.append(
            "premiumkort men "
            "spelaren har svag "
            "efterfrågan"
        )

    if (
        premium_like
        and profile["score"] < 70
        and total_cost >= 200
    ):
        value *= 0.82

        risks.append(
            "dyrt premiumkort "
            "på mellannamn"
        )

    if total_cost <= 30:
        value += 4

    value = max(
        0,
        round(value),
    )

    confidence = max(
        0.05,
        min(
            confidence,
            0.92,
        ),
    )

    return (
        value,
        confidence,
        reasons,
        risks,
        total_cost,
        features,
        profile,
    )


def compute_specificity(
    features,
    title,
):
    score = 0

    if features.get(
        "player_name"
    ):
        score += 25

    if features.get(
        "set_name"
    ):
        score += 20

    if features.get(
        "year"
    ):
        score += 8

    if (
        features.get(
            "serial_number"
        )
        is not None
    ):
        score += 12

    if features.get(
        "grade"
    ):
        score += 8

    if len(
        (
            title
            or ""
        ).split()
    ) >= 5:
        score += 8

    if features.get(
        "is_lot"
    ):
        score -= 20

    return max(
        0,
        min(
            score,
            100,
        ),
    )


def compute_liquidity(
    features,
    profile,
    total_cost,
    sport,
):
    score = (
        18
        + profile["score"]
        * 0.45
    )

    sets = (
        FOOTBALL_SETS
        if sport == "football"
        else HOCKEY_SETS
    )

    score += (
        sets.get(
            features.get(
                "set_name"
            ),
            0,
        )
        * 0.55
    )

    if features.get(
        "is_rookie"
    ):
        score += 6

    if features.get(
        "is_auto"
    ):
        score += 4

    if total_cost <= 150:
        score += 8

    if total_cost >= 800:
        score -= 15

    elif total_cost >= 500:
        score -= 9

    elif total_cost >= 300:
        score -= 4

    if profile["score"] < 40:
        score -= 12

    return round(
        max(
            0,
            min(
                score,
                100,
            ),
        ),
        1,
    )


def compute_sale_probability(
    liquidity,
    specificity,
    profile,
    comparable_count,
    risks,
    total_cost,
):
    score = (
        8
        + liquidity * 0.45
        + specificity * 0.12
        + profile["score"] * 0.18
    )

    score += min(
        comparable_count
        * 2.5,
        12,
    )

    if total_cost <= 150:
        score += 6

    elif total_cost >= 800:
        score -= 15

    elif total_cost >= 500:
        score -= 10

    elif total_cost >= 300:
        score -= 5

    if "premium trap" in risks:
        score -= 14

    if (
        "svag spelarmarknad"
        in risks
    ):
        score -= 10

    if "samlingsannons" in risks:
        score -= 8

    return round(
        max(
            5,
            min(
                score,
                95,
            ),
        ),
        1,
    )


def get_comp_info(
    item,
    all_items,
):
    if not all_items:
        return (
            None,
            0,
            None,
        )

    analysis = (
        build_market_analysis(
            item,
            all_items,
        )
    )

    if not analysis.get(
        "success"
    ):
        return (
            None,
            0,
            analysis,
        )

    count = analysis.get(
        "comparable_count",
        0,
    )

    stats = (
        analysis.get(
            "price_stats"
        )
        or {}
    )

    value = stats.get(
        "median_comparable_total_cost"
    )

    if value is None:
        value = stats.get(
            "median_comparable_price"
        )

    return (
        value,
        count,
        analysis,
    )


def compute_haircut(
    confidence,
    specificity,
    comparable_count,
    risks,
):
    haircut = 0.10

    if confidence < 0.35:
        haircut += 0.18

    elif confidence < 0.55:
        haircut += 0.10

    if specificity < 35:
        haircut += 0.12

    if comparable_count <= 1:
        haircut += 0.08

    if "premium trap" in risks:
        haircut += 0.10

    if (
        "svag spelarmarknad"
        in risks
    ):
        haircut += 0.08

    if "samlingsannons" in risks:
        haircut += 0.07

    return round(
        max(
            0.05,
            min(
                haircut,
                0.55,
            ),
        ),
        2,
    )


def compute_resale_ranges(
    estimated_value,
    haircut,
    profile,
    liquidity,
):
    if profile["score"] < 40:
        demand_multiplier = 0.72

    elif profile["score"] < 60:
        demand_multiplier = 0.86

    else:
        demand_multiplier = 1.0

    expected_multiplier = max(
        0.42,
        (
            1
            - haircut
        )
        * demand_multiplier,
    )

    floor_multiplier = max(
        0.30,
        expected_multiplier
        - 0.15,
    )

    best_multiplier = max(
        expected_multiplier,
        1.0
        + max(
            (
                liquidity
                - 60
            )
            / 250,
            0,
        ),
    )

    return (
        round(
            estimated_value
            * floor_multiplier
        ),
        round(
            estimated_value
            * expected_multiplier
        ),
        round(
            estimated_value
            * best_multiplier
        ),
    )


def compute_profit(
    total_cost,
    expected_resale,
    floor_resale,
    probability,
):
    outbound_shipping = (
        18
        if expected_resale <= 200
        else 36
    )

    selling_fee = round(
        expected_resale
        * 0.08
    )

    packaging = 3

    net_profit = (
        expected_resale
        - total_cost
        - outbound_shipping
        - selling_fee
        - packaging
    )

    floor_profit = (
        floor_resale
        - total_cost
        - outbound_shipping
        - round(
            floor_resale
            * 0.08
        )
        - packaging
    )

    risk_adjusted = (
        net_profit
        * probability
        / 100
    )

    roi = (
        net_profit
        / total_cost
        if total_cost
        else 0
    )

    return {
        "net_profit_estimate":
            round(
                net_profit,
                2,
            ),

        "floor_profit_estimate":
            round(
                floor_profit,
                2,
            ),

        "risk_adjusted_profit":
            round(
                risk_adjusted,
                2,
            ),

        "roi_estimate":
            round(
                roi,
                2,
            ),
    }


def compute_card_quality(
    features,
    profile,
    sport,
    confidence,
):
    score = 10

    score += (
        profile["score"]
        * 0.18
    )

    sets = (
        FOOTBALL_SETS
        if sport == "football"
        else HOCKEY_SETS
    )

    score += sets.get(
        features.get(
            "set_name"
        ),
        0,
    )

    if features.get(
        "is_rookie"
    ):
        score += 12

    if features.get(
        "is_auto"
    ):
        score += 18

    if features.get(
        "is_patch"
    ):
        score += 8

    if features.get(
        "is_low_serial"
    ):
        score += 12

    elif features.get(
        "is_mid_serial"
    ):
        score += 4

    score += (
        confidence
        * 8
    )

    return round(
        max(
            0,
            min(
                score,
                100,
            ),
        ),
        2,
    )


def compute_flip_scores(
    profits,
    probability,
    liquidity,
    quality,
    profile,
    total_cost,
    risks,
):
    if total_cost <= 100:
        affordability = 18

    elif total_cost <= 250:
        affordability = 10

    else:
        affordability = 0

    quick = (
        profits[
            "risk_adjusted_profit"
        ]
        + probability * 0.42
        + liquidity * 0.30
        + profile["score"] * 0.22
        + affordability
    )

    premium = (
        profits[
            "risk_adjusted_profit"
        ]
        * 0.78
        + quality * 0.34
        + probability * 0.24
        + liquidity * 0.20
        + profile["score"] * 0.20
    )

    if "premium trap" in risks:
        quick -= 22
        premium -= 30

    if profile["score"] < 40:
        quick -= 18
        premium -= 22

    return (
        round(
            quick,
            2,
        ),
        round(
            premium,
            2,
        ),
    )


def compute_rank(
    raw_score,
    quick,
    premium,
    quality,
    player_score,
    strategy_mode,
):
    if strategy_mode == "premium_flip":
        score = (
            premium * 0.55
            + quick * 0.15
            + quality * 0.10
            + player_score * 0.20
        )

    elif strategy_mode == "kort":
        score = (
            quality * 0.40
            + premium * 0.20
            + quick * 0.15
            + player_score * 0.25
        )

    else:
        score = (
            quick * 0.55
            + premium * 0.10
            + quality * 0.08
            + player_score * 0.27
        )

    score += (
        raw_score
        or 0
    ) * 0.02

    return round(
        score,
        2,
    )


def make_decision(
    net_profit,
    risk_adjusted,
    probability,
    player_score,
):
    if (
        player_score < 35
        and net_profit < 100
    ):
        return "SKIP"

    if (
        risk_adjusted >= 60
        and probability >= 65
        and net_profit >= 80
    ):
        return "KÖP (starkt fynd)"

    if (
        risk_adjusted >= 20
        and probability >= 55
        and net_profit >= 30
    ):
        return "KÖP"

    if (
        risk_adjusted >= 8
        and probability >= 40
        and net_profit >= 10
    ):
        return "KANSKE"

    return "SKIP"


def compute_exit_speed(
    liquidity,
    probability,
    total_cost,
):
    score = (
        liquidity * 0.6
        + probability * 0.4
    )

    if total_cost <= 150:
        score += 6

    if total_cost >= 800:
        score -= 10

    elif total_cost >= 500:
        score -= 5

    if score >= 75:
        return "Snabb"

    if score >= 55:
        return "Medel"

    return "Trög"


def build_invalid_result(
    item,
    sport,
    reason,
):
    return {
        "titel":
            item.get(
                "titel",
                "",
            ),

        "pris":
            item.get(
                "pris",
                0,
            )
            or 0,

        "frakt":
            item.get(
                "frakt"
            ),

        "total_cost":
            (
                item.get(
                    "pris",
                    0,
                )
                or 0
            )
            + (
                item.get(
                    "frakt"
                )
                or 0
            ),

        "player_name": None,
        "player_market_score": 0,
        "demand_tier": "weak",
        "sport": sport,

        "score":
            item.get(
                "score",
                0,
            )
            or 0,

        "uppskattat_varde": 0,
        "heuristic_estimated_value": 0,
        "comp_estimated_value": None,
        "value_source": "invalid",
        "marginal": 0,
        "confidence": 0.05,
        "rank_score": 0,
        "card_quality_score": 0,
        "hype_score": 0,
        "specificity_score": 0,
        "listing_weakness_score": 0,
        "mislist_potential": 0,
        "liquidity_score": 0,
        "sale_probability": 0,
        "uncertainty_haircut": 0.5,
        "floor_resale": 0,
        "expected_resale": 0,
        "best_case_resale": 0,
        "net_profit_estimate": 0,
        "floor_profit_estimate": 0,
        "risk_adjusted_profit": 0,
        "quick_flip_score": 0,
        "premium_flip_score": 0,
        "exit_speed": "Trög",
        "roi_estimate": 0,
        "beslut": "SKIP",
        "kommentar": reason,

        "lank":
            item.get(
                "lank",
                "",
            ),

        "sale_type":
            detect_sale_type(
                item
            ),

        "reasons": [
            reason
        ],

        "risk_flags": [
            reason
        ],

        "market_analysis_summary":
            None,

        "comparable_count": 0,

        "saljare":
            item.get(
                "saljare"
            ),

        "source_category":
            item.get(
                "source_category"
            ),
    }


def analyze_core(
    item,
    sport,
    strategy_mode,
    all_items=None,
    full=False,
):
    title = item.get(
        "titel",
        "",
    )

    price = item.get(
        "pris"
    )

    if (
        not isinstance(
            price,
            (
                int,
                float,
            ),
        )
        or price <= 0
    ):
        return build_invalid_result(
            item,
            sport,
            "pris saknas eller är felaktigt",
        )

    (
        heuristic,
        confidence,
        reasons,
        risks,
        total_cost,
        features,
        profile,
    ) = estimate_title_value(
        item,
        sport,
    )

    specificity = (
        compute_specificity(
            features,
            title,
        )
    )

    liquidity = (
        compute_liquidity(
            features,
            profile,
            total_cost,
            sport,
        )
    )

    comp_value = None
    comparable_count = 0
    market_summary = None

    estimated_value = heuristic
    value_source = "heuristic_only"

    # Hockey kan använda den befintliga
    # lokala marknadsanalysen.
    # Fotboll hålls separat så hockeycomps
    # inte påverkar fotboll.
    if (
        full
        and all_items
        and sport == "hockey"
    ):
        (
            comp_value,
            comparable_count,
            market,
        ) = get_comp_info(
            item,
            all_items,
        )

        if (
            market
            and market.get(
                "success"
            )
        ):
            market_summary = (
                market.get(
                    "summary"
                )
            )

        if (
            comp_value
            is not None
            and comparable_count >= 2
        ):
            if comparable_count >= 5:
                comp_weight = 0.45

            else:
                comp_weight = 0.35

            estimated_value = round(
                heuristic
                * (
                    1
                    - comp_weight
                )
                + comp_value
                * comp_weight
            )

            value_source = (
                "blended_current_listings"
            )

            confidence = min(
                0.92,
                confidence
                + (
                    0.08
                    if comparable_count >= 5
                    else 0.04
                ),
            )

            reasons.append(
                f"{comparable_count} "
                f"lokala aktuella "
                f"jämförelseannonser"
            )

    elif (
        full
        and sport == "football"
    ):
        reasons.append(
            "fotboll använder separat "
            "ranking utan hockeycomps"
        )

    probability = (
        compute_sale_probability(
            liquidity,
            specificity,
            profile,
            comparable_count,
            risks,
            total_cost,
        )
    )

    haircut = compute_haircut(
        confidence,
        specificity,
        comparable_count,
        risks,
    )

    (
        floor_resale,
        expected_resale,
        best_case_resale,
    ) = compute_resale_ranges(
        estimated_value,
        haircut,
        profile,
        liquidity,
    )

    profits = compute_profit(
        total_cost,
        expected_resale,
        floor_resale,
        probability,
    )

    quality = compute_card_quality(
        features,
        profile,
        sport,
        confidence,
    )

    (
        quick_score,
        premium_score,
    ) = compute_flip_scores(
        profits,
        probability,
        liquidity,
        quality,
        profile,
        total_cost,
        risks,
    )

    rank = compute_rank(
        item.get(
            "score",
            0,
        )
        or 0,
        quick_score,
        premium_score,
        quality,
        profile["score"],
        strategy_mode,
    )

    decision = make_decision(
        profits[
            "net_profit_estimate"
        ],
        profits[
            "risk_adjusted_profit"
        ],
        probability,
        profile["score"],
    )

    try:
        comment = build_comment(
            item,
            expected_resale,
            confidence,
            reasons,
        )

    except Exception:
        comment = "; ".join(
            reasons[:3]
        )

    return {
        "titel": title,
        "pris": price,
        "frakt":
            item.get(
                "frakt"
            ),

        "total_cost":
            total_cost,

        "player_name":
            profile["name"],

        "player_market_score":
            profile["score"],

        "demand_tier":
            profile["tier"],

        "sport":
            sport,

        "score":
            item.get(
                "score",
                0,
            )
            or 0,

        "uppskattat_varde":
            expected_resale,

        "heuristic_estimated_value":
            heuristic,

        "comp_estimated_value":
            (
                round(
                    comp_value
                )
                if comp_value
                is not None
                else None
            ),

        "value_source":
            value_source,

        "marginal":
            expected_resale
            - total_cost,

        "confidence":
            round(
                confidence,
                2,
            ),

        "rank_score":
            rank,

        "card_quality_score":
            quality,

        "hype_score":
            profile["score"],

        "specificity_score":
            specificity,

        "listing_weakness_score":
            max(
                0,
                100
                - specificity,
            ),

        "mislist_potential":
            max(
                0,
                70
                - specificity,
            ),

        "liquidity_score":
            liquidity,

        "sale_probability":
            probability,

        "uncertainty_haircut":
            haircut,

        "floor_resale":
            floor_resale,

        "expected_resale":
            expected_resale,

        "best_case_resale":
            best_case_resale,

        "net_profit_estimate":
            profits[
                "net_profit_estimate"
            ],

        "floor_profit_estimate":
            profits[
                "floor_profit_estimate"
            ],

        "risk_adjusted_profit":
            profits[
                "risk_adjusted_profit"
            ],

        "quick_flip_score":
            quick_score,

        "premium_flip_score":
            premium_score,

        "exit_speed":
            compute_exit_speed(
                liquidity,
                probability,
                total_cost,
            ),

        "roi_estimate":
            profits[
                "roi_estimate"
            ],

        "beslut":
            decision,

        "kommentar":
            comment,

        "lank":
            item.get(
                "lank",
                "",
            ),

        "sale_type":
            detect_sale_type(
                item
            ),

        "reasons":
            reasons,

        "risk_flags":
            risks,

        "market_analysis_summary":
            market_summary,

        "comparable_count":
            comparable_count,

        "saljare":
            item.get(
                "saljare"
            ),

        "source_category":
            item.get(
                "source_category"
            ),
    }


def analyze_item_fast(
    item,
    strategy_mode="quick_flip",
    sport="hockey",
):
    return analyze_core(
        item,
        sport=sport,
        strategy_mode=strategy_mode,
        all_items=None,
        full=False,
    )


def analyze_item_full(
    item,
    all_items=None,
    strategy_mode="quick_flip",
    sport="hockey",
):
    return analyze_core(
        item,
        sport=sport,
        strategy_mode=strategy_mode,
        all_items=(
            all_items
            or []
        ),
        full=True,
    )


def analyze_item(
    item,
    all_items=None,
    mode="full",
    strategy_mode="quick_flip",
    sport="hockey",
):
    if mode == "fast":
        return analyze_item_fast(
            item,
            strategy_mode=
                strategy_mode,
            sport=sport,
        )

    return analyze_item_full(
        item,
        all_items=all_items,
        strategy_mode=
            strategy_mode,
        sport=sport,
    )