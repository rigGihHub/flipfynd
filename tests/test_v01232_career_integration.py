from pathlib import Path

def test_career_context_wired():
    analyzer=Path("src/analyzer.py").read_text(encoding="utf-8")
    explanation=Path("src/card_explanation.py").read_text(encoding="utf-8")
    assert "build_career_era_context(" in analyzer
    assert '"career_context_verified"' in analyzer
    assert "Verifierad karriärkontext:" in explanation
