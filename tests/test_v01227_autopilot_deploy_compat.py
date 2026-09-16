from pathlib import Path

def test_removed_autopilot_ui_has_no_runtime_dependency():
    app=Path("app.py").read_text(encoding="utf-8")
    compat=Path("src/autopilot_compat.py").read_text(encoding="utf-8")
    assert "from src.autopilot_compat" not in app
    assert "inspect.signature" in compat
    assert '"analyzed_results" in params' in compat
