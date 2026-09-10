from pathlib import Path

def test_ui_has_active_supply_action_and_scope_warning():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Kontrollera aktivt Tradera-utbud" in app
    assert "unika träffar observerades" in app
    assert "Kontrollera aktivt Tradera-utbud" in app
