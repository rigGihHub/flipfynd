import json
from typing import Any


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def estimate_tokens_from_text(text: str) -> int:
    """
    Grov uppskattning:
    ungefär 1 token per 4 tecken för blandad text.
    Inte exakt, men användbar som kostnadsestimat.
    """
    if not text:
        return 0

    chars = len(text)
    return max(1, round(chars / 4))


def estimate_tokens_from_payload(payload: Any) -> int:
    text = _to_text(payload)
    return estimate_tokens_from_text(text)


def estimate_ai_call_tokens(
    system_prompt: str,
    user_payload: Any,
    expected_output_tokens: int = 400,
) -> dict:
    input_text = _to_text({
        "system_prompt": system_prompt,
        "user_payload": user_payload,
    })

    estimated_input_tokens = estimate_tokens_from_text(input_text)

    return {
        "estimated_input_tokens": estimated_input_tokens,
        "estimated_output_tokens": max(1, int(expected_output_tokens)),
        "estimated_total_tokens": estimated_input_tokens + max(1, int(expected_output_tokens)),
        "estimated_input_characters": len(input_text),
    }