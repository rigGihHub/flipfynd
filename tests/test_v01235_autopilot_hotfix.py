from pathlib import Path

def test_app_uses_compat_wrapper():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "build_autopilot_plan_compat(" in app
    assert 'APP_VERSION = "v0.12.51"' in app
