from src.comp_research_workbench import (
    build_research_links,
    fetch_sportscardspro_context,
    parse_verified_sales_batch,
)


def identity():
    return {
        "player_name": "Wayne Gretzky",
        "set_name": "Pinnacle",
        "season": "1995-96",
        "card_number": "101",
    }


def test_links_use_structured_exact_identity():
    result = build_research_links(identity())
    assert result["ready"] is True
    assert "Wayne Gretzky" in result["query"]
    urls = {row["key"]: row["url"] for row in result["links"]}
    assert "LH_Sold=1" in urls["ebay"]
    assert "sportscardspro.com/search-products" in urls["sportscardspro"]


def test_batch_capture_requires_explicit_verification():
    result = parse_verified_sales_batch(
        "eBay | 2.15 | USD | 9.50 | 2026-09-01 | https://example.com/sale",
        identity(),
        identity_verified=False,
        identity_evidence_source="checklist",
        sales_confirmed=True,
    )
    assert result["valid_count"] == 0
    assert result["errors"]


def test_batch_capture_builds_multiple_strict_sales():
    text = "\n".join([
        "eBay | 2.15 | USD | 9.50 | 2026-09-01 | https://example.com/ebay",
        "Tradera | 24 | SEK | | 2026-08-20 | https://example.com/tradera",
    ])
    result = parse_verified_sales_batch(
        text,
        identity(),
        identity_verified=True,
        identity_evidence_source="checklist + photo",
        sales_confirmed=True,
    )
    assert result["valid_count"] == 2
    assert not result["errors"]
    assert result["rows"][0]["identity_verified"] is True
    assert result["rows"][1]["source_platform"] == "Tradera"


def test_sportscardspro_requires_token_without_network_call():
    result = fetch_sportscardspro_context(identity(), token="")
    assert result["ok"] is False
    assert result["status"] == "TOKEN_MISSING"
