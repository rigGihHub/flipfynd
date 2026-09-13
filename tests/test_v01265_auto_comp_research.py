from src.auto_comp_research import identity_from_item, research_one, run_auto_comp_research


def item(sold=0, ready=True):
    return {
        "title": "2021-22 MVP #119 Nicklas Backstrom Silver Script",
        "sold_comparable_count": sold,
        "exact_identity_gate_supports_exact_comp_search": ready,
        "exact_identity_gate_identity_fields": {
            "player_name": "Nicklas Backstrom",
            "set_name": "MVP",
            "season": "2021-22",
            "card_number": "119",
            "parallel": "Silver Script",
        },
    }


def test_identity_uses_structured_gate_only():
    assert identity_from_item(item())["card_number"] == "119"
    assert identity_from_item({"title": "Wayne Gretzky #101"}) == {}


def test_unverified_identity_stays_locked():
    out = research_one(item(ready=False), [])
    assert out["status"] == "IDENTITY_FIRST"
    assert out["creates_sold_evidence"] is False


def test_batch_runner_never_creates_sales_or_buy_decision():
    out = run_auto_comp_research([item(), item()], [], limit=1)
    assert out["processed_count"] == 1
    assert out["rows"][0]["creates_sold_evidence"] is False
    assert out["rows"][0]["creates_buy_decision"] is False
    assert out["rows"][0]["missing_exact_sales"] == 2


def test_research_links_exist_for_ready_identity():
    out = research_one(item(), [])
    labels = {x["label"] for x in out["research_links"]}
    assert "eBay Sold" in labels
    assert "Tradera" in labels
