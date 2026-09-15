from pathlib import Path


def test_app_opens_with_secondary_seller_sidebar_collapsed():
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    config = app[app.index("st.set_page_config("):app.index(")", app.index("st.set_page_config("))]
    assert 'initial_sidebar_state="collapsed"' in config
    assert 'APP_VERSION = "v0.14.5"' in app
