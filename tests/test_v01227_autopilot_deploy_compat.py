from pathlib import Path

def test_autopilot_call_remains_deploy_safe():
    app=Path("app.py").read_text(encoding="utf-8")
    compat=Path("src/autopilot_compat.py").read_text(encoding="utf-8")
    assert "build_autopilot_plan_compat(" in app
    assert "inspect.signature" in compat
    assert '"analyzed_results" in params' in compat
