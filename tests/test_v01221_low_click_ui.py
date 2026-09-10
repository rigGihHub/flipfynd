from pathlib import Path
def test_low_click_research_still_present():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "build_low_click_action_plan" in app
    assert "src.research_action_center" in app
