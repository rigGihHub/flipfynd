import statistics
from typing import List, Optional

from src.card_parser import parse_card_features

PREMIUM_SETS = {"The Cup", "SP Authentic", "Dominion", "Premier", "Ultimate Collection", "Black Diamond"}


def _safe_total_cost(item: dict) -> Optional[float]:
    price = item.get("pris")
    if price is None or not isinstance(price, (int, float)) or price <= 0:
        return None

    shipping = item.get("frakt")
    shipping = 0 if shipping is None else shipping

    if not isinstance(shipping, (int, float)):
        shipping = 0

    return float(price + shipping)


def _normalize_features(item: dict) -> dict:
    title = item.get("titel", "") or ""
    features = parse_card_features(title)

    player_name = features.get("player_name")
    if player_name:
        aliases = {
            "Connor Mcdavid": "Connor McDavid",
            "Nathan Mackinnon": "Nathan MacKinnon",
            "Nils Hoglander": "Nils Hoglander",
        }
        features["player_name"] = aliases.get(player_name, player_name)

    return features


def _same_last_name(name1: Optional[str], name2: Optional[str]) -> bool:
    if not name1 or not name2:
        return False

    parts1 = name1.split()
    parts2 = name2.split()
    if not parts1 or not parts2:
        return False

    return parts1[-1].lower() == parts2[-1].lower()


def _is_premium(features: dict) -> bool:
    return (
        features.get("set_name") in PREMIUM_SETS
        or features.get("is_auto")
        or features.get("is_patch")
        or features.get("is_low_serial")
    )


def _serial_bucket(features: dict) -> str:
    serial = features.get("serial_number")

    if serial is None:
        return "none"
    if serial <= 10:
        return "ultra_low"
    if serial <= 25:
        return "very_low"
    if serial <= 50:
        return "low"
    if serial <= 99:
        return "mid_low"
    if serial <= 199:
        return "mid"
    if serial <= 499:
        return "high"
    return "very_high"


def score_similarity(base_item: dict, other_item: dict) -> int:
    if base_item.get("lank") == other_item.get("lank"):
        return -999

    base_features = _normalize_features(base_item)
    other_features = _normalize_features(other_item)

    score = 0

    base_player = base_features.get("player_name")
    other_player = other_features.get("player_name")

    if base_player and other_player:
        if base_player == other_player:
            score += 24
        elif _same_last_name(base_player, other_player):
            score += 4
        else:
            score -= 18
    elif bool(base_player) != bool(other_player):
        score -= 8

    base_set = base_features.get("set_name")
    other_set = other_features.get("set_name")

    if base_set and other_set:
        if base_set == other_set:
            score += 14
        else:
            score -= 10
    elif bool(base_set) != bool(other_set):
        score -= 5

    base_year = base_features.get("year")
    other_year = other_features.get("year")

    if base_year and other_year:
        if base_year == other_year:
            score += 5
        elif abs(base_year - other_year) == 1:
            score += 1
        elif abs(base_year - other_year) >= 3:
            score -= 4

    base_parallel = base_features.get("parallel")
    other_parallel = other_features.get("parallel")

    if base_parallel and other_parallel:
        if base_parallel == other_parallel:
            score += 6
        else:
            score -= 6
    elif bool(base_parallel) != bool(other_parallel):
        score -= 3

    if base_features.get("is_rookie") == other_features.get("is_rookie"):
        score += 4
    else:
        score -= 5

    if base_features.get("is_auto") == other_features.get("is_auto"):
        score += 6
    else:
        score -= 8

    if base_features.get("is_patch") == other_features.get("is_patch"):
        score += 4
    else:
        score -= 5

    if base_features.get("is_graded") == other_features.get("is_graded"):
        score += 5
    else:
        score -= 8

    if base_features.get("is_lot") == other_features.get("is_lot"):
        score += 2
    else:
        score -= 16

    base_premium = _is_premium(base_features)
    other_premium = _is_premium(other_features)
    if base_premium == other_premium:
        score += 4
    else:
        score -= 8

    base_serial_bucket = _serial_bucket(base_features)
    other_serial_bucket = _serial_bucket(other_features)
    if base_serial_bucket == other_serial_bucket:
        score += 6
    elif base_serial_bucket == "none" or other_serial_bucket == "none":
        score -= 2
    else:
        score -= 6

    base_serial = base_features.get("serial_number")
    other_serial = other_features.get("serial_number")
    if base_serial is not None and other_serial is not None:
        if base_serial == other_serial:
            score += 4
        elif abs(base_serial - other_serial) <= 10:
            score += 2
        elif abs(base_serial - other_serial) >= 200:
            score -= 4

    return score


def _filter_by_price_distance(base_total_cost: float, candidates: List[dict]) -> List[dict]:
    filtered = []

    for item in candidates:
        total_cost = _safe_total_cost(item)
        if total_cost is None:
            continue

        if base_total_cost <= 100:
            if total_cost <= max(base_total_cost * 2.4, 180):
                filtered.append(item)
        elif base_total_cost <= 300:
            if total_cost <= base_total_cost * 2.2 and total_cost >= base_total_cost * 0.35:
                filtered.append(item)
        else:
            if total_cost <= base_total_cost * 2.0 and total_cost >= base_total_cost * 0.40:
                filtered.append(item)

    return filtered


def _remove_outliers(prices: List[float]) -> List[float]:
    if len(prices) < 4:
        return prices

    sorted_prices = sorted(prices)
    q1 = statistics.median(sorted_prices[: len(sorted_prices) // 2])
    if len(sorted_prices) % 2 == 0:
        upper_half = sorted_prices[len(sorted_prices) // 2 :]
    else:
        upper_half = sorted_prices[len(sorted_prices) // 2 + 1 :]
    q3 = statistics.median(upper_half) if upper_half else q1

    iqr = q3 - q1
    if iqr == 0:
        return sorted_prices

    low_bound = q1 - 1.5 * iqr
    high_bound = q3 + 1.5 * iqr

    cleaned = [p for p in sorted_prices if low_bound <= p <= high_bound]
    return cleaned if cleaned else sorted_prices


def _trimmed_median(prices: List[float]) -> float:
    if not prices:
        return 0.0

    sorted_prices = sorted(prices)
    n = len(sorted_prices)

    if n <= 4:
        return float(statistics.median(sorted_prices))

    trim = max(1, int(round(n * 0.15)))
    if n - (trim * 2) < 2:
        return float(statistics.median(sorted_prices))

    trimmed = sorted_prices[trim : n - trim]
    return float(statistics.median(trimmed))


def _comp_confidence(comparable_count: int, similarity_scores: List[int]) -> str:
    if comparable_count >= 8 and similarity_scores and statistics.median(similarity_scores) >= 34:
        return "hög"
    if comparable_count >= 5 and similarity_scores and statistics.median(similarity_scores) >= 28:
        return "medel"
    return "låg"


def build_market_analysis(item: dict, all_items: list) -> dict:
    current_price = item.get("pris")
    current_total_cost = _safe_total_cost(item)

    if current_price is None or current_price <= 0 or current_total_cost is None:
        return {
            "success": False,
            "error": "Objektet saknar giltigt pris.",
        }

    if not all_items:
        return {
            "success": True,
            "comparable_count": 0,
            "summary": "Ingen lokal data att jämföra mot.",
            "price_stats": None,
            "sample_titles": [],
            "verdict": "För lite data.",
            "confidence": "låg",
        }

    scored = []

    for other in all_items:
        if not isinstance(other, dict):
            continue

        other_total_cost = _safe_total_cost(other)
        if other_total_cost is None:
            continue

        sim = score_similarity(item, other)

        if sim >= 22:
            scored.append((sim, other))

    scored.sort(
        key=lambda x: (
            -x[0],
            abs((_safe_total_cost(x[1]) or 0) - current_total_cost),
        )
    )

    rough_candidates = [x[1] for x in scored[:20]]
    rough_candidates = _filter_by_price_distance(current_total_cost, rough_candidates)

    rescored = []
    for other in rough_candidates:
        sim = score_similarity(item, other)
        if sim >= 22:
            rescored.append((sim, other))

    rescored.sort(
        key=lambda x: (
            -x[0],
            abs((_safe_total_cost(x[1]) or 0) - current_total_cost),
        )
    )

    comparables = [x[1] for x in rescored[:10]]
    similarity_scores = [x[0] for x in rescored[:10]]

    if len(comparables) < 2:
        return {
            "success": True,
            "comparable_count": len(comparables),
            "summary": "För få tydligt liknande annonser hittades i din egen data. Lokala comps är för svaga för att väga tungt.",
            "price_stats": None,
            "sample_titles": [x.get("titel", "") for x in comparables[:5]],
            "verdict": "För lite data.",
            "confidence": "låg",
        }

    prices = []
    totals = []

    for comp in comparables:
        price = comp.get("pris")
        total = _safe_total_cost(comp)
        if isinstance(price, (int, float)) and price > 0:
            prices.append(float(price))
        if total is not None:
            totals.append(float(total))

    if len(prices) < 2 or len(totals) < 2:
        return {
            "success": True,
            "comparable_count": len(comparables),
            "summary": "Liknande annonser hittades, men prisunderlaget är för tunt eller trasigt.",
            "price_stats": None,
            "sample_titles": [x.get("titel", "") for x in comparables[:5]],
            "verdict": "För lite data.",
            "confidence": "låg",
        }

    cleaned_totals = _remove_outliers(totals)
    cleaned_prices = _remove_outliers(prices)

    median_total = statistics.median(cleaned_totals)
    median_price = statistics.median(cleaned_prices)
    trimmed_total = _trimmed_median(cleaned_totals)

    min_total = min(cleaned_totals)
    max_total = max(cleaned_totals)

    confidence = _comp_confidence(len(comparables), similarity_scores)

    benchmark_total = min(median_total, trimmed_total) if confidence == "låg" else trimmed_total

    if current_total_cost < benchmark_total * 0.68:
        verdict = "Tydligt billigt"
    elif current_total_cost < benchmark_total * 0.82:
        verdict = "Ganska billigt"
    elif current_total_cost > benchmark_total * 1.30:
        verdict = "Dyrt"
    else:
        verdict = "Nära marknadspris"

    summary_parts = [
        "Baseras på de mest liknande annonserna i din lokala data.",
        "Jämförelsen använder främst total kostnad (pris + frakt), inte bara listpris.",
    ]

    if confidence == "låg":
        summary_parts.append("Comp-kvaliteten är låg, så analysen bör ses som grov vägledning snarare än hårt marknadsvärde.")
    elif confidence == "medel":
        summary_parts.append("Comp-kvaliteten är okej men inte superstark.")
    else:
        summary_parts.append("Comp-kvaliteten är relativt stark för lokal data.")

    return {
        "success": True,
        "comparable_count": len(comparables),
        "summary": " ".join(summary_parts),
        "price_stats": {
            "current_price": round(float(current_price), 2),
            "current_total_cost": round(current_total_cost, 2),
            "median_comparable_price": round(float(median_price), 2),
            "median_comparable_total_cost": round(float(median_total), 2),
            "trimmed_median_total_cost": round(float(trimmed_total), 2),
            "min_comparable_price": round(float(min(cleaned_prices)), 2),
            "max_comparable_price": round(float(max(cleaned_prices)), 2),
            "min_comparable_total_cost": round(float(min_total), 2),
            "max_comparable_total_cost": round(float(max_total), 2),
        },
        "sample_titles": [x.get("titel", "") for x in comparables[:5]],
        "verdict": verdict,
        "confidence": confidence,
    }