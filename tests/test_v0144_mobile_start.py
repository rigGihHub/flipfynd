from pathlib import Path


def test_app_opens_with_secondary_seller_sidebar_collapsed():
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    config = app[app.index("st.set_page_config("):app.index(")", app.index("st.set_page_config("))]
    assert 'initial_sidebar_state="collapsed"' in config
    assert 'APP_VERSION = "v0.14.16"' in app


def test_mobile_start_closes_browser_restored_sidebar_only_once():
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "_mobile_sidebar_normalized_v0147" in app
    assert "window.parent.innerWidth > 768" in app
    assert "keyboard_double_arrow_left" in app
    assert "closeButton.click()" in app
