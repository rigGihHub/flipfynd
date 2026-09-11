from pathlib import Path

def test_rookie_window_is_wired_into_analyzer_and_ui():
    analyzer=Path("src/analyzer.py").read_text(encoding="utf-8")
    app=Path("app.py").read_text(encoding="utf-8")
    assert "build_rookie_window_context(" in analyzer
    assert '"rookie_claim_support"' in analyzer
    assert "Spelararketyp:" in app
    assert "kronologiskt tveksamt" in app
