from src.analyzer import compute_profit
from src.listing_detail_enrichment import parse_detail_text
from src.find_diagnostics import summarize_no_find_reasons


def test_profit_uses_current_private_tradera_fee_and_no_double_shipping():
    result = compute_profit(45, 35, 30, 79)
    # 35 - 45 - min fee 3.5 - packaging 3 = -16.5
    assert result["net_profit_estimate"] == -16.5
    assert result["profit_breakdown"]["outbound_shipping_cost"] == 0
    assert result["profit_breakdown"]["selling_fee"] == 3.5


def test_detail_page_shipping_is_captured():
    result = parse_detail_text("Pris 1 kr Frakt 22 kr Säljare: Testaren")
    assert result["detail_shipping"] == 22
    assert result["detail_shipping_source"] == "Tradera-annons"


def test_no_find_summary_uses_primary_blocker():
    result = summarize_no_find_reasons([
        {"beslut": "SKIP", "exact_identity_gate_status": "LÅST", "exact_identity_gate_score": 20},
        {"beslut": "SKIP", "exact_identity_gate_status": "SÖKBAR", "exact_identity_gate_score": 80, "valuation_confidence": 40, "comparable_count": 1},
    ])
    counts = {x["label"]: x["count"] for x in result["reasons"]}
    assert counts["Osäker kortidentitet"] == 1
    assert counts["För svagt prisunderlag"] == 1
