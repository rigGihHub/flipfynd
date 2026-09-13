from src.unlock_research_queue import build_unlock_research_queue


def _item(title, *, guide=None, merit=0):
    item = {
        "titel": title,
        "deal_score": 80,
        "sold_comparable_count": 0,
        "exact_identity_gate_supports_exact_comp_search": True,
        "exact_identity_gate_supports_comp_research": True,
        "collector_worth_score": merit,
        "card_hierarchy_score": merit,
        "exact_identity_gate_identity_fields": {
            "player_name": title,
            "set_name": "Set",
            "season": "2024-25",
            "card_number": "1",
        },
    }
    if guide is not None:
        item["guide_triage"] = {
            "status": "LOW_GUIDE_CONTEXT",
            "priority": 3,
            "ungraded_usd": guide,
        }
    return item


def test_low_guide_exact_id_is_demoted_below_stronger_candidate():
    cheap = _item("Cheap superstar insert", guide=1.5, merit=30)
    strong = _item("Numbered rookie target", merit=75)
    strong["is_rookie"] = True
    strong["rookie_importance_score"] = 90
    strong["serial_denominator"] = 99

    out = build_unlock_research_queue([cheap, strong], limit=2)

    assert out["rows"][0]["title"] == "Numbered rookie target"
    assert out["rows"][1]["title"] == "Cheap superstar insert"
    assert out["rows"][1]["status"] == "EXACT_READY_LOW_GUIDE"
    assert out["rows"][1]["guide_ungraded_usd"] == 1.5


def test_exact_id_with_weak_merit_no_longer_gets_normal_exact_status():
    weak = _item("Ordinary exact-id card", merit=5)
    out = build_unlock_research_queue([weak], limit=1)
    assert out["rows"][0]["status"] == "EXACT_READY_LOW_MERIT"
