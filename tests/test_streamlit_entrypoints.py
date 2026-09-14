from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_flipfynd_has_one_streamlit_entrypoint():
    """Seller Top 5 belongs in app.py, not Streamlit multipage navigation."""
    pages_dir = ROOT / "pages"
    page_scripts = list(pages_dir.glob("*.py")) if pages_dir.exists() else []

    assert page_scripts == []
    assert (ROOT / "app.py").is_file()


def test_seller_top5_is_integrated_in_main_app():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert 'with st.sidebar.expander("🏪 Säljare – Top 5 kort"' in app_source
    assert 'key="seller_top5_profile_url"' in app_source
    assert 'key="seller_top5_run"' in app_source
