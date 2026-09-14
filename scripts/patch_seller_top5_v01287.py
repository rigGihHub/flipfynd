from pathlib import Path

# FlipFynd v0.12.87 — make partial Seller Top 5 batches return quickly.
# The previous implementation ran the full ordinary analyser over every item
# already loaded after EACH 5-page batch. That could exceed Streamlit's request
# lifetime, so the user saw no Top 5 and the search appeared to abort.

p = Path('src/seller_top5_controller.py')
text = p.read_text(encoding='utf-8')

if 'from src.seller_collector_signals import collector_signals' not in text:
    text = text.replace(
        'from src.seller_top5 import build_seller_top5\n',
        'from src.seller_top5 import build_seller_top5\nfrom src.seller_collector_signals import collector_signals\nfrom src.seller_card_domain import seller_item_domain_check\n',
        1,
    )

start = text.find('def _partial_result_from_saved(')
end = text.find('\n\ndef resolve_seller_top5(', start)
if start >= 0 and end > start:
    replacement = '''def _partial_result_from_saved(\n    alias: str,\n    saved_items: dict[str, dict],\n    *,\n    analyze_fn: Callable,\n    quick_limit: int,\n    full_limit: int,\n    progress_callback,\n    ui,\n    public_status: str,\n    public_error,\n    pages_read: int,\n    next_page: int,\n    api_status: str,\n    fallback_reason: str,\n    resume_required: bool,\n    total_listing_estimate: int | None = None,\n):\n    \"\"\"Return a provisional Top 5 without invoking the expensive analyser.\n\n    Partial seller inventories are intentionally ranked with cheap title/domain\n    signals only. The full ordinary FlipFynd analysis still runs once the whole\n    seller inventory is loaded. This keeps each 5-page request short enough for\n    Streamlit while still showing the best five candidates found so far.\n    \"\"\"\n    candidates = []\n    rejected = 0\n    for item in saved_items.values():\n        if not isinstance(item, dict):\n            continue\n        check = seller_item_domain_check(item, sport=\"all\")\n        if not check.get(\"allowed\"):\n            rejected += 1\n            continue\n        sig = collector_signals(item)\n        title = str(item.get(\"titel\") or item.get(\"title\") or \"Kortannons\").strip()\n        price = item.get(\"pris\") if item.get(\"pris\") is not None else item.get(\"price\")\n        try:\n            price_num = float(price) if price is not None else None\n        except (TypeError, ValueError):\n            price_num = None\n        # Collector signals are the primary provisional sort. Small secondary\n        # bonuses surface recognisable card products/rookies/parallels while\n        # low price only breaks otherwise similar candidates.\n        lower = title.casefold()\n        product_bonus = sum(\n            token in lower\n            for token in (\n                \"upper deck\", \"topps\", \"panini\", \"o-pee-chee\", \"opc\",\n                \"prizm\", \"chrome\", \"young guns\", \"rookie\", \"parallel\",\n                \"refractor\", \"dazzlers\", \"red edition\", \"patch\", \"auto\",\n            )\n        )\n        score = min(100.0, float(sig.get(\"score\") or 0) * 2.0 + product_bonus * 3.0)\n        candidates.append({\n            \"title\": title,\n            \"price\": price_num,\n            \"url\": item.get(\"lank\") or item.get(\"url\") or item.get(\"link\"),\n            \"decision\": \"UNDERSÖK\",\n            \"label\": \"PRELIMINÄR KANDIDAT\",\n            \"reason\": \"Preliminär ranking av inlästa annonser. Slutlig ranking görs när hela profilen är läst.\",\n            \"rank_score\": score,\n            \"player_market_score\": 0,\n            \"risk_adjusted_profit\": 0,\n            \"sold_comps\": 0,\n            \"market_edge\": 0,\n            \"valuation_confidence\": 0,\n            \"collector_signal_score\": int(sig.get(\"score\") or 0),\n            \"collector_signals\": list(sig.get(\"signals\") or []),\n            \"analysis_level\": \"provisional_title_triage\",\n            \"source_item\": item,\n            \"seller\": alias,\n        })\n\n    candidates.sort(key=lambda row: (\n        -float(row.get(\"rank_score\") or 0),\n        row.get(\"price\") if row.get(\"price\") is not None else 10**12,\n        str(row.get(\"title\") or \"\"),\n    ))\n    rows = candidates[:5]\n    loaded = len(saved_items)\n    remaining = max(0, int(total_listing_estimate) - loaded) if total_listing_estimate else None\n    return {\n        \"seller\": alias,\n        \"rows\": rows,\n        \"status\": \"INVENTORY_PARTIAL\",\n        \"inventory_count\": loaded,\n        \"card_inventory_count\": len(candidates),\n        \"domain_rejected_count\": rejected,\n        \"inventory_source\": \"TRADERA_PUBLIC_PROFILE\",\n        \"public_status\": public_status,\n        \"public_error\": public_error,\n        \"public_pages_read\": pages_read,\n        \"public_next_page\": next_page,\n        \"public_batch_pages\": 0,\n        \"public_inventory_complete\": False,\n        \"provisional_top5\": bool(rows),\n        \"resume_required\": bool(resume_required),\n        \"fallback_reason\": fallback_reason,\n        \"api_status\": api_status,\n        \"total_listing_estimate\": total_listing_estimate,\n        \"remaining_listing_estimate\": remaining,\n        \"quick_analysed\": 0,\n        \"full_analysed\": 0,\n        \"ranking_source\": \"PROVISIONAL_TITLE_TRIAGE\",\n    }\n'''
    text = text[:start] + replacement + text[end:]

p.write_text(text, encoding='utf-8')

p = Path('app.py')
text = p.read_text(encoding='utf-8')
text = text.replace('APP_VERSION = "v0.12.86"', 'APP_VERSION = "v0.12.87"')
text = text.replace('APP_VERSION = "v0.12.85"', 'APP_VERSION = "v0.12.87"')
# Do not show full-analysis metrics for the lightweight provisional list.
text = text.replace(
    'st.caption("Samma rankingmotor som i ordinarie FlipFynd-sökningen.")',
    'st.caption("Slutlig ranking använder samma analysmotor som ordinarie FlipFynd-sökningen.")',
)
text = text.replace(
    'if row.get("analysis_level") == "quick_fallback":\n                    st.caption("Preliminär snabbanalys.")',
    'if row.get("analysis_level") in {"quick_fallback", "provisional_title_triage"}:\n                    st.caption("Preliminär kandidat · full analys görs senare.")',
)
p.write_text(text, encoding='utf-8')

print('patched FlipFynd v0.12.87: fast provisional Seller Top 5 between batches')
