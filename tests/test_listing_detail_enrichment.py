from src.listing_detail_enrichment import (
    extract_jsonld_detail,
    parse_detail_text,
    score_detail_priority,
    select_detail_candidates,
)


def test_priority_prefers_structured_chase_listing():
    strong, reasons = score_detail_priority({"titel": "Connor Bedard Young Guns High Gloss 07/10"})
    plain, _ = score_detail_priority({"titel": "Connor Bedard hockeykort vanlig bas"})
    assert strong > plain
    assert "serial" in reasons
    assert "rookie_program" in reasons


def test_short_generic_title_gets_detail_review_priority():
    score, reasons = score_detail_priority({"titel": "Bedard rookie"})
    assert score >= 12
    assert "kort/generisk titel" in reasons


def test_new_listings_are_selected_before_known_listings():
    items = [
        {"titel": "Known PMG /10", "lank": "https://x/item/1"},
        {"titel": "New base card", "lank": "https://x/item/2"},
    ]
    selected = select_detail_candidates(items, known_links={"https://x/item/1"}, limit=1)
    assert selected[0]["lank"] == "https://x/item/2"


def test_parse_detail_text_reads_bid_count_and_end_text():
    parsed = parse_detail_text("12 bud   Auktionen avslutas: 3 sep 21:14   Frakt 29 kr")
    assert parsed["bid_count"] == 12
    assert "3 sep 21:14" in parsed["exact_end_text"]


def test_jsonld_extracts_description_and_images():
    html = '''<html><script type="application/ld+json">{
      "@type":"Product", "name":"Card #123", "description":"Full card description",
      "image":["https://img/1.jpg","https://img/2.jpg"]
    }</script></html>'''
    parsed = extract_jsonld_detail(html)
    assert parsed["detail_title"] == "Card #123"
    assert parsed["full_description"] == "Full card description"
    assert len(parsed["detail_image_urls"]) == 2


def test_priority_output_contains_no_valuation_fields():
    score, reasons = score_detail_priority({"titel": "Rookie auto /25"})
    payload = {"detail_priority_score": score, "detail_priority_reasons": reasons}
    forbidden = {"market_value", "profit", "roi", "max_bid", "max_purchase_price"}
    assert forbidden.isdisjoint(payload)
