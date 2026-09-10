from pathlib import Path

def test_supply_vs_sales_ui_and_version():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Supply vs SOLD" in app
    assert "deskriptiv jämförelse" in app
    assert "skapar inte efterfrågesignal" in app
    assert "Supply vs SOLD" in app
