from pathlib import Path

def test_confirmation_ui_and_version():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "bekräftade exakta" in app
    assert "möjliga" in app
    assert "fel kort/konflikt" in app
    assert "bekräftad exakt match, möjlig match eller fel kort" in app
    assert "bekräftade exakta" in app
