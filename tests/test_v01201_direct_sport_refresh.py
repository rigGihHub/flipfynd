from pathlib import Path


def test_advanced_fetch_has_direct_refresh_buttons_for_both_sports():
    app = Path('app.py').read_text(encoding='utf-8')
    assert '🏒 Uppdatera gamla sidor – Hockey' in app
    assert '⚽ Uppdatera gamla sidor – Fotboll' in app
    assert 'start_fetch("Hockey - NHL", True, "scheduled_refresh")' in app
    assert 'start_fetch("Fotboll", True, "scheduled_refresh")' in app


def test_advanced_fetch_radio_removed_but_onboarding_radio_preserved():
    app = Path('app.py').read_text(encoding='utf-8')
    assert 'key="main_fetch_scope"' not in app
    assert 'key="onboarding_fetch_scope"' in app


def test_each_refresh_button_uses_its_own_due_state():
    app = Path('app.py').read_text(encoding='utf-8')
    assert 'not refresh_h.get("due")' in app
    assert 'not refresh_f.get("due")' in app
