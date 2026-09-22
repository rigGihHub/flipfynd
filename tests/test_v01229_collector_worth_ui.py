from pathlib import Path

def test_collector_worth_ui_and_version():
    analyzer=Path("src/analyzer.py").read_text(encoding="utf-8")
    explanation=Path("src/card_explanation.py").read_text(encoding="utf-8")
    assert '"collector_worth_score"' in analyzer
    assert "Samlarprofil:" in explanation
    assert "Samlarfälla:" in explanation
