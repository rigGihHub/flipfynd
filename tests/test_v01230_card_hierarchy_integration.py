from pathlib import Path

def test_hierarchy_wired_into_analyzer_and_ui():
    analyzer=Path("src/analyzer.py").read_text(encoding="utf-8")
    app=Path("app.py").read_text(encoding="utf-8")
    assert "build_card_hierarchy_engine(" in analyzer
    assert '"card_hierarchy_score"' in analyzer
    assert "Hobbyhierarki:" in app
