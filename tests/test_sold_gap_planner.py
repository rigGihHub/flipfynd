from src.sold_gap_planner import build_sold_research_queue


def exact_sold(player="A", set_name="Set", season="2025-26", card_number="10"):
    return {
        "titel": f"{player} {set_name} #{card_number}",
        "sold_price": 100,
        "sold_verification_status": "verified",
        "sale_evidence_type": "explicit_sold_price",
        "player_name": player,
        "set_name": set_name,
        "season": season,
        "card_number": card_number,
        "identity_verified": True,
        "identity_evidence_source": "manual_review",
    }


def candidate(player="A", set_name="Set", season="2025-26", card_number="10", score=50):
    return {
        "titel": f"{player} card",
        "beslut": "BEVAKA",
        "opportunity_priority_score": score,
        "exact_identity_gate_identity_fields": {
            "player_name": player,
            "set_name": set_name,
            "season": season,
            "card_number": card_number,
        },
    }


def test_queue_marks_no_exact_sold():
    out = build_sold_research_queue([candidate()], [], limit=10)
    assert out["no_exact_sold_count"] == 1
    assert out["rows"][0]["status"] == "NO_EXACT_SOLD"


def test_queue_counts_exact_ready_sales_only():
    sold = exact_sold()
    unverified = dict(sold)
    unverified["sold_verification_status"] = ""
    out = build_sold_research_queue([candidate()], [sold, unverified], limit=10)
    assert out["thin_exact_sold_count"] == 1
    assert out["rows"][0]["exact_sold_count"] == 1


def test_queue_requires_structured_identity():
    c = {"titel": "Player Set #10", "beslut": "SKIP", "opportunity_priority_score": 99}
    out = build_sold_research_queue([c], [exact_sold()], limit=10)
    assert out["identity_first_count"] == 1
    assert out["rows"][0]["status"] == "IDENTITY_FIRST"


def test_queue_prioritizes_missing_exact_before_existing():
    rows = [candidate(player="B", score=10), candidate(player="A", score=90)]
    sold = [exact_sold(player="A"), exact_sold(player="A")]
    out = build_sold_research_queue(rows, sold, limit=10)
    assert out["rows"][0]["identity"]["player_name"] == "B"
    assert out["rows"][0]["status"] == "NO_EXACT_SOLD"
