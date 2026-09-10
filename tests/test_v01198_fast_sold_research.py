from pathlib import Path
from src.sold_research_assist import build_quick_capture_defaults, research_progress


def test_quick_defaults_never_invent_sale_facts():
    d = build_quick_capture_defaults({
        "player_name": "A", "set_name": "Set", "season": "2025", "card_number": "1"
    })
    assert d["sold_price"] == 0.0
    assert d["sold_url"] == ""
    assert d["sold_at"] == ""
    assert d["sale_confirmed"] is False
    assert d["identity_verified"] is False


def test_research_progress_one_sale_left():
    p = research_progress(1, target=2)
    assert p["remaining"] == 1
    assert p["complete"] is False


def test_research_progress_target_reached():
    p = research_progress(2, target=2)
    assert p["remaining"] == 0
    assert p["complete"] is True


def test_fast_research_ui_copy_present():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "Snabbregistrera verifierat avslut" in app
    assert "Du fyller bara i sådant FlipFynd inte får gissa." in app
    assert "Kör om analysen för att använda det nya underlaget." in app
