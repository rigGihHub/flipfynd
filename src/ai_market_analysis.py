import json
import os
from typing import Any

from src.token_estimator import estimate_ai_call_tokens


SYSTEM_PROMPT = """
Du analyserar annonser för hockeykort på Tradera.

Regler:
- Var kritisk, realistisk och undvik glädjekalkyler.
- Bygg analysen primärt på annonsens titel, pris och råtext.
- Om information saknas ska du säga att osäkerheten är hög.
- Utgå inte från att kortet är äkta, graderat eller i toppskick om det inte framgår.
- Blanda inte ihop aktiva listpriser med faktiska avslutade försäljningar.
- Svara endast med giltig JSON enligt det schema som efterfrågas.
""".strip()


def build_ai_payload(item: dict, all_items: list[dict], comparable_limit: int = 5) -> dict:
    current_link = item.get("lank", "")
    current_price = item.get("pris")
    current_title = item.get("titel", "")

    comparables = []
    for other in all_items:
        if other.get("lank") == current_link:
            continue

        other_title = other.get("titel", "")
        other_price = other.get("pris")

        if not other_title or other_price is None:
            continue

        title_words = set(current_title.lower().split())
        other_words = set(other_title.lower().split())
        overlap = len(title_words.intersection(other_words))

        if overlap >= 2:
            comparables.append({
                "titel": other_title,
                "pris": other_price,
                "lank": other.get("lank", ""),
                "overlap": overlap,
            })

    comparables.sort(
        key=lambda x: (x["overlap"], -abs((x["pris"] or 0) - (current_price or 0))),
        reverse=True
    )
    comparables = comparables[:comparable_limit]

    return {
        "listing": {
            "titel": item.get("titel", ""),
            "pris": item.get("pris"),
            "raw_text": item.get("raw_text", ""),
            "lank": item.get("lank", ""),
        },
        "local_comparables": [
            {
                "titel": c["titel"],
                "pris": c["pris"],
                "lank": c["lank"],
            }
            for c in comparables
        ],
        "instructions": {
            "currency": "SEK",
            "goal": "Assess likely fair value range and whether the listing looks undervalued, fairly priced, or overpriced.",
            "warning": "Local comparables are active listings, not sold prices.",
        },
    }


def get_ai_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "identified_player": {"type": "string"},
            "identified_set": {"type": "string"},
            "identified_card_type": {"type": "string"},
            "estimated_value_low_sek": {"type": "number"},
            "estimated_value_high_sek": {"type": "number"},
            "confidence": {"type": "number"},
            "risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"]
            },
            "assessment": {
                "type": "string",
                "enum": ["undervalued", "fair", "overpriced", "unclear"]
            },
            "reasons": {
                "type": "array",
                "items": {"type": "string"}
            },
            "warning_flags": {
                "type": "array",
                "items": {"type": "string"}
            },
            "short_summary": {"type": "string"}
        },
        "required": [
            "identified_player",
            "identified_set",
            "identified_card_type",
            "estimated_value_low_sek",
            "estimated_value_high_sek",
            "confidence",
            "risk_level",
            "assessment",
            "reasons",
            "warning_flags",
            "short_summary"
        ]
    }


def build_ai_market_analysis(
    item: dict,
    all_items: list[dict],
    model: str = "gpt-5.4-mini",
    dry_run: bool = True,
    expected_output_tokens: int = 450,
) -> dict:
    payload = build_ai_payload(item, all_items)
    token_estimate = estimate_ai_call_tokens(
        system_prompt=SYSTEM_PROMPT,
        user_payload=payload,
        expected_output_tokens=expected_output_tokens,
    )

    result = {
        "success": True,
        "dry_run": dry_run,
        "model": model,
        "token_estimate": token_estimate,
        "request_preview": payload,
    }

    if dry_run:
        result["summary"] = (
            "Dry run: inget API-anrop gjordes. "
            "Det här läget kostar inget och visar bara uppskattat underlag och tokennivå."
        )
        return result

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "dry_run": dry_run,
            "model": model,
            "token_estimate": token_estimate,
            "error": "OPENAI_API_KEY saknas i miljövariablerna."
        }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        schema = get_ai_response_schema()

        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": SYSTEM_PROMPT,
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(payload, ensure_ascii=False),
                        }
                    ],
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "hockey_card_market_analysis",
                    "schema": schema,
                    "strict": True,
                }
            },
        )

        if getattr(response, "output_text", None):
            parsed_output = json.loads(response.output_text)
        else:
            return {
                "success": False,
                "dry_run": dry_run,
                "model": model,
                "token_estimate": token_estimate,
                "error": "Modellen returnerade ingen text att tolka."
            }

        usage = getattr(response, "usage", None)
        usage_dict = None
        if usage:
            usage_dict = {
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }

        return {
            "success": True,
            "dry_run": dry_run,
            "model": model,
            "token_estimate": token_estimate,
            "usage": usage_dict,
            "analysis": parsed_output,
            "summary": parsed_output.get("short_summary", ""),
        }

    except Exception as e:
        return {
            "success": False,
            "dry_run": dry_run,
            "model": model,
            "token_estimate": token_estimate,
            "error": str(e)
        }