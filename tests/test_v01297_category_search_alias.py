from pathlib import Path


def test_category_words_are_not_used_as_literal_listing_keywords():
    app = Path("app.py").read_text(encoding="utf-8")

    assert '"fotbollskort"' in app
    assert '"football cards"' in app
    assert '"hockeykort"' in app
    assert "search=effective_search" in app
    assert "APP_VERSION = \"v0.12.97\"" in app
