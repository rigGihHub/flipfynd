import src.auto_comp_research as research


def _item(title):
    return {
        "titel": title,
        "exact_identity_gate_supports_exact_comp_search": True,
        "exact_identity_gate_supports_comp_research": True,
        "exact_identity_gate_status": "READY",
        "exact_identity_gate_identity_fields": {
            "player_name": "Nathan MacKinnon",
            "set_name": "Upper Deck Series 1",
            "season": "2024-25",
            "card_number": "GFOV-12",
        },
    }


def test_low_raw_guide_is_research_triage_only(monkeypatch):
    monkeypatch.setattr(
        research,
        "fetch_sportscardspro_context",
        lambda identity, token=None: {
            "ok": True,
            "status": "CONTEXT_ONLY",
            "ungraded_usd": 1.50,
        },
    )

    row = research.research_one(_item("MacKinnon low value insert"), sold_records=[], scp_token="token")

    assert row["status"] == "LOW_GUIDE_CONTEXT"
    assert row["guide_triage"]["status"] == "LOW_GUIDE_CONTEXT"
    assert row["guide_triage"]["ungraded_usd"] == 1.5
    assert row["exact_sold_count"] == 0
    assert row["creates_sold_evidence"] is False
    assert row["creates_buy_decision"] is False
    assert "Guide ~$1.50 raw" in row["next_action"]
    assert "inte en verifierad försäljning" in row["next_action"]


def test_low_guide_context_sorts_after_normal_research_target():
    normal = {
        "title": "Strong research target",
        "status": "TWO_EXACT_SALES_NEEDED",
        "missing_exact_sales": 2,
        "guide_triage": {"priority": 1},
    }
    cheap = {
        "title": "Cheap guide card",
        "status": "LOW_GUIDE_CONTEXT",
        "missing_exact_sales": 2,
        "guide_triage": {"priority": 3},
    }

    rows = [cheap, normal]
    rows.sort(key=research._batch_sort_key)

    assert rows[0]["title"] == "Strong research target"
    assert rows[1]["title"] == "Cheap guide card"


def test_two_verified_sales_are_not_demoted_by_guide_context(monkeypatch):
    monkeypatch.setattr(
        research,
        "fetch_sportscardspro_context",
        lambda identity, token=None: {
            "ok": True,
            "status": "CONTEXT_ONLY",
            "ungraded_usd": 1.25,
        },
    )
    monkeypatch.setattr(
        research,
        "hunt_exact_comps",
        lambda candidate, observed_records=None: {"exact_sold_count": 2, "near_sold_count": 0},
    )

    row = research.research_one(_item("Threshold met"), sold_records=[], scp_token="token")

    assert row["status"] == "LOCAL_THRESHOLD_MET"
    assert row["exact_sold_count"] == 2


def test_batch_exposes_only_three_best_research_actions(monkeypatch):
    def fake_research_one(item, sold_records=None, scp_token=None):
        title = item["titel"]
        cheap = title.startswith("cheap")
        return {
            "title": title,
            "identity_ready": True,
            "research_identity_ready": True,
            "exact_sold_count": 0,
            "missing_exact_sales": 2,
            "status": "LOW_GUIDE_CONTEXT" if cheap else "TWO_EXACT_SALES_NEEDED",
            "guide_triage": {"priority": 3 if cheap else 1, "status": "LOW_GUIDE_CONTEXT" if cheap else "NO_GUIDE_CONTEXT"},
        }

    monkeypatch.setattr(research, "research_one", fake_research_one)
    items = [
        {"titel": "cheap 1"},
        {"titel": "strong A"},
        {"titel": "strong B"},
        {"titel": "strong C"},
        {"titel": "cheap 2"},
    ]

    pack = research.run_auto_comp_research(items, sold_records=[], limit=5)

    assert pack["processed_count"] == 5
    assert pack["displayed_count"] == 3
    assert pack["hidden_after_triage_count"] == 2
    assert [row["title"] for row in pack["rows"]] == ["strong A", "strong B", "strong C"]
