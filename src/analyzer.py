import re

from src.card_parser import parse_card_features
from src.comments import build_comment
from src.market_analysis import build_market_analysis
from src.player_market import get_player_database, match_player, normalize_player_name
from src.pricing import normalize_shipping, total_acquisition_cost


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
    return normalize_player_name(name)


def detect_known_player(title, sport):
    return match_player(title, sport).get('name')


def detect_player_match(title, sport):
    return match_player(title, sport)


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

    player_match = detect_player_match(
        title,
        sport,
    )

    if player_match.get("name"):
        features["player_name"] = player_match["name"]
        features["player_match_confidence"] = player_match.get("confidence", "high")
        features["player_match_type"] = player_match.get("match_type", "exact")
    else:
        # Parserns fallback kan vara användbar som texttolkning, men den ska
        # inte behandlas som en säker marknadsidentifiering.
        features["player_name"] = normalize_name(features.get("player_name"))
        features["player_match_confidence"] = "low"
        features["player_match_type"] = "parser_fallback"

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
    # Prefer a structured value if the fetcher or an imported source already
    # provides one. The current Tradera fetcher normally falls back to raw_text.
    explicit = str(item.get("sale_type") or "").strip().casefold()
    if explicit in {"köp nu", "kop nu", "buy now", "buy it now"}:
        return "Köp nu"
    if explicit in {"auktion", "auction"}:
        return "Auktion"

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


def compute_entry_cost(item, total_cost):
    """Return a conservative acquisition cost for ranking and profit math.

    A Buy-now price is executable at the displayed amount. An auction price is
    only the current/starting price and can rise before closing. We therefore
    add a modest auction buffer so an early low bid does not masquerade as a
    guaranteed flip margin. The original displayed total_cost is kept intact.
    """
    if total_cost is None:
        return None, 0

    if detect_sale_type(item) != "Auktion":
        return float(total_cost), 0

    price = float(item.get("pris") or 0)
    # Minimum buffer matters on cheap cards; the cap prevents the heuristic
    # from dominating expensive auctions where we lack bid-history data.
    buffer = round(max(15.0, min(price * 0.12, 75.0)), 2)
    return round(float(total_cost) + buffer, 2), buffer


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
            "match_confidence": "low",
        }

    if player_name in database:
        score, tier = database[player_name]
        return {
            "name": player_name,
            "score": score,
            "tier": tier,
            "match_confidence": features.get("player_match_confidence", "high"),
        }

    # Okända parserträffar ska inte få ett artificiellt medium-score.
    # Hellre försiktig osäkerhet än falsk precision.
    score = 25
    if features.get("is_rookie"):
        score += 5

    return {
        "name": player_name,
        "score": min(score, 35),
        "tier": "weak",
        "match_confidence": features.get("player_match_confidence", "low"),
    }



def collectible_demand_factor(player_score):
    """Scale premium traits by actual player demand instead of treating them as universal value.

    Serial numbering, autos and memorabilia can make a card scarcer, but scarcity on a
    weak player does not create the same resale market as scarcity on an elite name.
    """
    score = float(player_score or 0)
    if score >= 85:
        return 1.00
    if score >= 70:
        return 0.85
    if score >= 55:
        return 0.65
    if score >= 40:
        return 0.45
    return 0.25


def premium_trait_bonus(features, player_score):
    """Return conservative title-derived premium bonus and supporting reasons.

    This is deliberately not a market valuation. It only adjusts the heuristic until
    stronger comparable-price evidence exists.
    """
    demand = collectible_demand_factor(player_score)
    bonus = 0.0
    confidence_bonus = 0.0
    reasons = []

    if features.get("is_auto"):
        bonus += 24 * demand
        confidence_bonus += 0.04 * demand
        reasons.append("autograf")

    if features.get("is_patch") or features.get("is_jersey"):
        bonus += 9 * demand
        confidence_bonus += 0.02 * demand
        reasons.append("patch/relic")

    if features.get("is_game_worn"):
        bonus += 8 * demand
        confidence_bonus += 0.015 * demand
        reasons.append("game/match worn")

    serial = features.get("serial_number")
    if features.get("is_1of1"):
        # Even a 1/1 has scarcity value, but title-only valuation is highly uncertain.
        scarcity_factor = max(0.45, demand)
        bonus += 40 * scarcity_factor
        confidence_bonus += 0.025 * demand
        reasons.append("1/1")
    elif serial is not None:
        if serial <= 10:
            raw_bonus = 30
        elif serial <= 25:
            raw_bonus = 22
        elif serial <= 50:
            raw_bonus = 15
        elif serial <= 99:
            raw_bonus = 9
        elif serial <= 199:
            raw_bonus = 4
        else:
            raw_bonus = 1
        bonus += raw_bonus * max(0.35, demand)
        reasons.append(f"numrerat /{serial}")

    return round(bonus), confidence_bonus, reasons


def rookie_trait_bonus(features, player_score, player_match_confidence="low"):
    """Conservative rookie premium tied to demand *and* rookie-program quality.

    A generic RC label is only a small positive signal. Named flagship rookie
    programs (for example Young Guns or Future Watch Auto) can add more value,
    but only when the player market is strong. This prevents "rookie" from
    becoming a universal shortcut to a high valuation.
    """
    if not features.get("is_rookie"):
        return 0, 0.0, [], []

    demand = collectible_demand_factor(player_score)
    variant = str(features.get("rookie_variant") or "Generic Rookie")
    tier = str(features.get("rookie_tier") or "standard").lower()

    base_bonus = 10
    variant_bonus = {
        "iconic": 14,
        "strong": 7,
        "standard": 0,
    }.get(tier, 0)

    # Weak/unknown names still receive only a small fraction of any rookie premium.
    demand_floor = 0.22 if tier == "standard" else 0.28
    bonus = round((base_bonus + variant_bonus) * max(demand_floor, demand))

    confidence_bonus = 0.0
    reasons = ["rookie/RC"]
    risks = []

    if variant != "Generic Rookie":
        reasons.append(f"rookieprogram: {variant}")

    specific = bool(features.get("year") or features.get("set_name") or variant != "Generic Rookie")
    if player_match_confidence in {"high", "medium"} and specific:
        confidence_bonus = (0.025 + (0.012 if tier == "iconic" else 0.006 if tier == "strong" else 0.0)) * demand
    else:
        risks.append("rookieetikett är inte fullt verifierad mot år/set")

    if float(player_score or 0) < 55:
        risks.append("rookiekort på svag spelarmarknad")
        if tier in {"iconic", "strong"}:
            risks.append("känt rookieprogram väger inte upp svag spelarefterfrågan")

    if tier == "standard" and not features.get("set_name"):
        risks.append("generisk rookieetikett utan identifierat rookieprogram")

    return bonus, confidence_bonus, reasons, risks


def grading_trait_bonus(features, player_score):
    """Value recognized grading conservatively instead of treating every slab equally."""
    grade = str(features.get("grade") or "").upper().strip()
    company = str(features.get("grading_company") or "").upper().strip()
    if not grade:
        return 0, 0.0, [], []

    match = re.search(r"(10|9\.5|9|8\.5|8|7\.5|7|6)$", grade)
    if not match:
        return 0, 0.0, ["graderat"], ["graderingsnivå kunde inte tolkas säkert"]

    numeric = float(match.group(1))
    demand = collectible_demand_factor(player_score)
    raw = 0

    if company == "PSA":
        raw = 18 if numeric >= 10 else 8 if numeric >= 9 else 2 if numeric >= 8 else 0
    elif company == "BGS":
        raw = 20 if numeric >= 10 else 14 if numeric >= 9.5 else 6 if numeric >= 9 else 1 if numeric >= 8.5 else 0
    elif company == "SGC":
        raw = 14 if numeric >= 10 else 8 if numeric >= 9.5 else 5 if numeric >= 9 else 1 if numeric >= 8 else 0
    else:
        return 0, 0.0, ["graderat"], ["okänt graderingsbolag ger inget automatiskt värdepåslag"]

    bonus = round(raw * max(0.30, demand))
    confidence_bonus = 0.015 * demand if raw > 0 else 0.0
    reasons = [f"{company} {numeric:g}"]
    risks = []

    if numeric < 9:
        risks.append("lägre grade ger begränsad premie")
    if float(player_score or 0) < 55 and raw > 0:
        risks.append("graderingspremie begränsas av svag spelarmarknad")

    return bonus, confidence_bonus, reasons, risks


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

    shipping = normalize_shipping(
        item.get("frakt")
    )

    total_cost = total_acquisition_cost(
        price,
        item.get("frakt"),
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

    player_match_confidence = profile.get("match_confidence", "low")
    if player_match_confidence == "medium":
        confidence -= 0.03
        reasons.append("spelarnamn identifierat med viss stavningstolerans")
    elif player_match_confidence == "low":
        confidence -= 0.10
        risks.append("osäker spelaridentifiering")

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

    rookie_bonus, rookie_confidence, rookie_reasons, rookie_risks = rookie_trait_bonus(
        features,
        profile["score"],
        profile.get("match_confidence", "low"),
    )
    value += rookie_bonus
    confidence += rookie_confidence
    reasons.extend(rookie_reasons)
    risks.extend(rookie_risks)

    premium_bonus, premium_confidence, premium_reasons = premium_trait_bonus(
        features,
        profile["score"],
    )
    value += premium_bonus
    confidence += premium_confidence
    reasons.extend(premium_reasons)

    serial = features.get(
        "serial_number"
    )

    if premium_reasons and profile["score"] < 55:
        risks.append(
            "premiumegenskaper har begränsad värdeeffekt på svag spelarmarknad"
        )

    grade_bonus, grade_confidence, grade_reasons, grade_risks = grading_trait_bonus(
        features,
        profile["score"],
    )
    value += grade_bonus
    confidence += grade_confidence
    reasons.extend(grade_reasons)
    risks.extend(grade_risks)

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
        score += 6 * collectible_demand_factor(profile["score"])

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


def compute_comp_weight(comparable_count, comp_confidence):
    """Weight active-listing comps conservatively.

    These are asking prices, not confirmed sold prices. Low-confidence local
    comps therefore get only a small influence even when two or more exist.
    """
    if comparable_count < 2:
        return 0.0

    level = str(comp_confidence or "låg").casefold()

    if level == "hög":
        return 0.50 if comparable_count >= 5 else 0.40

    if level == "medel":
        return 0.40 if comparable_count >= 5 else 0.30

    return 0.20 if comparable_count >= 5 else 0.15


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
        score += 12 * collectible_demand_factor(profile["score"])

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

    profit_signal = min(max(profits["risk_adjusted_profit"], -50), 140)
    roi_signal = min(max(profits.get("roi_estimate", 0) * 100, -50), 180)

    quick = (
        profit_signal * 0.72
        + roi_signal * 0.18
        + probability * 0.42
        + liquidity * 0.30
        + profile["score"] * 0.25
        + affordability
    )

    premium = (
        profit_signal * 0.62
        + roi_signal * 0.10
        + quality * 0.34
        + probability * 0.24
        + liquidity * 0.20
        + profile["score"] * 0.22
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
    confidence=0.0,
    player_match_confidence="low",
    floor_profit=0.0,
    roi=0.0,
    total_cost=0.0,
):
    """Turn analysis into a conservative buy/watch/skip decision.

    A flip should not become a clear buy merely because the optimistic expected
    profit is large. The decision also needs reasonable capital efficiency and
    a tolerable downside in the conservative resale case.
    """
    if confidence < 0.28 or player_match_confidence == "low":
        return "SKIP"

    if (
        player_score < 35
        and net_profit < 100
    ):
        return "SKIP"

    capital = max(float(total_cost or 0), 1.0)
    downside_ratio = float(floor_profit or 0) / capital

    # A very poor floor case is not a buy, even if the expected case looks good.
    if downside_ratio < -0.40:
        if risk_adjusted >= 8 and probability >= 40 and net_profit >= 10:
            return "KANSKE"
        return "SKIP"

    if (
        risk_adjusted >= 60
        and probability >= 65
        and net_profit >= 80
        and roi >= 0.35
        and downside_ratio >= -0.15
    ):
        return "KÖP (starkt fynd)"

    if (
        risk_adjusted >= 20
        and probability >= 55
        and net_profit >= 30
        and roi >= 0.18
        and downside_ratio >= -0.25
    ):
        return "KÖP"

    if (
        risk_adjusted >= 8
        and probability >= 40
        and net_profit >= 10
        and roi >= 0.08
    ):
        return "KANSKE"

    return "SKIP"


def build_decision_diagnostics(
    decision,
    net_profit,
    risk_adjusted,
    probability,
    player_score,
    confidence,
    player_match_confidence,
    floor_profit,
    roi,
    total_cost,
):
    """Explain the most relevant gaps to the normal KÖP threshold."""
    if decision in {"KÖP", "KÖP (starkt fynd)"}:
        return []

    diagnostics = []
    capital = max(float(total_cost or 0), 1.0)
    downside_ratio = float(floor_profit or 0) / capital

    if confidence < 0.28:
        diagnostics.append(f"Analyssäkerhet {confidence:.0%}; minst 28 % krävs för ett köpbeslut.")
    if player_match_confidence == "low":
        diagnostics.append("Spelaren är inte identifierad tillräckligt säkert för ett köpbeslut.")
    if player_score < 35 and net_profit < 100:
        diagnostics.append(f"Spelarefterfrågan är låg ({player_score}/100) och vinsten kompenserar inte risken.")
    if downside_ratio < -0.25:
        diagnostics.append(f"Konservativt scenario motsvarar {downside_ratio:.0%} av inköpskostnaden; KÖP kräver minst -25 %.")
    if risk_adjusted < 20:
        diagnostics.append(f"Riskjusterad vinst {risk_adjusted:.0f} kr; KÖP kräver minst 20 kr.")
    if probability < 55:
        diagnostics.append(f"Säljchans {probability:.0f} %; KÖP kräver minst 55 %.")
    if net_profit < 30:
        diagnostics.append(f"Förväntad nettovinst {net_profit:.0f} kr; KÖP kräver minst 30 kr.")
    if roi < 0.18:
        diagnostics.append(f"Förväntad ROI {roi:.0%}; KÖP kräver minst 18 %.")

    # Keep the UI focused on the blockers that matter most.
    return diagnostics[:5]


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
            total_acquisition_cost(
                item.get("pris"),
                item.get("frakt"),
            )
            or 0,

        "player_name": None,
        "player_market_score": 0,
        "demand_tier": "weak",
        "player_match_confidence": "low",
        "player_match_type": "none",
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

    analysis_total_cost, auction_buffer = compute_entry_cost(
        item,
        total_cost,
    )
    sale_type = detect_sale_type(item)
    if sale_type == "Auktion" and auction_buffer > 0:
        risks.append("auktionspris kan stiga före avslut")
        reasons.append(
            f"auktion: {auction_buffer:.0f} kr säkerhetsmarginal används i fyndkalkylen"
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
            analysis_total_cost,
            sport,
        )
    )

    comp_value = None
    comparable_count = 0
    market_summary = None

    estimated_value = heuristic
    value_source = "heuristic_only"

    # Lokal comp-analys används för båda sporterna. Anroparen ska skicka
    # sportfiltrerad data så hockey- och fotbollsannonser aldrig blandas.
    if (
        full
        and all_items
        and sport in {"hockey", "football"}
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
            comp_confidence = (market or {}).get("confidence", "låg")
            comp_weight = compute_comp_weight(comparable_count, comp_confidence)

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

            # Aktiva annonser är utrops-/köp nu-priser, inte bekräftade avslut.
            # Bara medel/hög comp-kvalitet får därför höja analysens confidence.
            if str(comp_confidence).casefold() in {"medel", "hög"}:
                confidence = min(
                    0.92,
                    confidence
                    + (
                        0.08
                        if comp_confidence == "hög" and comparable_count >= 5
                        else 0.04
                    ),
                )

            reasons.append(
                f"{comparable_count} "
                f"lokala aktuella "
                f"jämförelseannonser "
                f"({comp_confidence} comp-kvalitet)"
            )


    probability = (
        compute_sale_probability(
            liquidity,
            specificity,
            profile,
            comparable_count,
            risks,
            analysis_total_cost,
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
        analysis_total_cost,
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
        analysis_total_cost,
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
        profits["net_profit_estimate"],
        profits["risk_adjusted_profit"],
        probability,
        profile["score"],
        confidence=confidence,
        player_match_confidence=profile.get("match_confidence", "low"),
        floor_profit=profits["floor_profit_estimate"],
        roi=profits["roi_estimate"],
        total_cost=analysis_total_cost,
    )

    decision_diagnostics = build_decision_diagnostics(
        decision,
        profits["net_profit_estimate"],
        profits["risk_adjusted_profit"],
        probability,
        profile["score"],
        confidence,
        profile.get("match_confidence", "low"),
        profits["floor_profit_estimate"],
        profits["roi_estimate"],
        analysis_total_cost,
    )

    # Kommentaren ska bygga på samma beräknade analysvärden
    # som returneras till användaren. Tidigare skickades originalannonsen
    # in här, vilket gjorde att build_comment ofta föll tillbaka på
    # standardvärden för efterfrågan, likviditet och riskjusterad vinst.
    comment_context = dict(item)
    comment_context.update({
        "demand_tier": profile["tier"],
        "sale_probability": probability,
        "liquidity_score": liquidity,
        "risk_adjusted_profit": profits["risk_adjusted_profit"],
        "quick_flip_score": quick_score,
        "premium_flip_score": premium_score,
        "value_source": value_source,
        "comparable_count": comparable_count,
        "risk_flags": risks,
    })

    try:
        comment = build_comment(
            comment_context,
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

        "analysis_total_cost":
            analysis_total_cost,

        "auction_buffer":
            auction_buffer,

        "sale_type":
            sale_type,

        "decision_diagnostics":
            decision_diagnostics,

        "player_name":
            profile["name"],

        "player_market_score":
            profile["score"],

        "demand_tier":
            profile["tier"],

        "player_match_confidence": profile.get("match_confidence", "low"),
        "player_match_type": features.get("player_match_type", "none"),

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
            sale_type,

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