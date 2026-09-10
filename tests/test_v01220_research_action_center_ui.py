from pathlib import Path

def test_action_center_still_integrated():
    app=Path('app.py').read_text(encoding='utf-8')
    assert 'build_low_click_action_plan' in app
    assert 'src.research_action_center' in app
    assert 'Research Action Center' in Path('src/research_action_center.py').read_text(encoding='utf-8')
