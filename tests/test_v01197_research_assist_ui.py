from pathlib import Path


def test_research_assist_ui_present():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "Research-assistent" in app
    assert ("Registrera ett verifierat avslut" in app or "Snabbregistrera verifierat avslut" in app)
    assert "Jag har verifierat att detta var en faktisk genomförd försäljning" in app
    assert "Explicit valutakurs till SEK" in app
