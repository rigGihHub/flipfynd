from pathlib import Path

def test_player_knowledge_wired_into_analyzer_and_ui():
    analyzer=Path("src/analyzer.py").read_text(encoding="utf-8")
    app=Path("app.py").read_text(encoding="utf-8")
    assert "get_player_knowledge(" in analyzer
    assert '"player_knowledge_verified"' in analyzer
    assert "Spelarkunskap:" in app
    assert "Spelarkunskap – täckning" in app
