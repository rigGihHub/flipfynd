"""The former per-sport buttons now share a single sport selector."""
from pathlib import Path


def test_refresh_has_one_shared_sport_selector():
    app = Path("app.py").read_text(encoding="utf-8")
    assert app.count('key="onboarding_fetch_scope"') == 1
    assert 'start_fetch(fetch_category, True, "latest")' in app


def test_older_fetch_modes_share_one_advanced_action():
    app = Path("app.py").read_text(encoding="utf-8")
    assert 'start_fetch(fetch_category, True, extra_modes[extra_mode])' in app
    assert "Uppdatera gamla sidor – Hockey" not in app
    assert "Uppdatera gamla sidor – Fotboll" not in app


def test_admin_has_no_duplicate_refresh_actions():
    app = Path("app.py").read_text(encoding="utf-8")
    admin = app[app.index('with st.expander("⚙️ Administration & data"):'):]
    assert "start_fetch(" not in admin
    assert "stop_fetch(" not in admin
