MODEL_PRICES_USD_PER_1M = {
    "gpt-5.4-mini": {
        "input": 0.75,
        "output": 4.50,
    },
    "gpt-5.4": {
        "input": 2.50,
        "output": 15.00,
    },
    "gpt-5.4-nano": {
        "input": 0.20,
        "output": 1.25,
    },
}


def estimate_ai_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    prices = MODEL_PRICES_USD_PER_1M.get(model)
    if not prices:
        raise ValueError(f"Okänd modell: {model}")

    input_cost = (max(input_tokens, 0) / 1_000_000) * prices["input"]
    output_cost = (max(output_tokens, 0) / 1_000_000) * prices["output"]
    return round(input_cost + output_cost, 6)


def estimate_ai_cost_sek(
    model: str,
    input_tokens: int,
    output_tokens: int,
    usd_to_sek: float,
) -> float:
    usd_cost = estimate_ai_cost_usd(model, input_tokens, output_tokens)
    return round(usd_cost * usd_to_sek, 4)


def estimate_period_costs(
    model: str,
    input_tokens: int,
    output_tokens: int,
    analyses_per_day: int,
    usd_to_sek: float,
) -> dict:
    per_call_usd = estimate_ai_cost_usd(model, input_tokens, output_tokens)
    per_call_sek = round(per_call_usd * usd_to_sek, 4)

    daily_usd = round(per_call_usd * max(analyses_per_day, 0), 4)
    daily_sek = round(daily_usd * usd_to_sek, 2)

    monthly_usd = round(daily_usd * 30, 2)
    monthly_sek = round(daily_sek * 30, 2)

    return {
        "per_call_usd": per_call_usd,
        "per_call_sek": per_call_sek,
        "daily_usd": daily_usd,
        "daily_sek": daily_sek,
        "monthly_usd": monthly_usd,
        "monthly_sek": monthly_sek,
    }