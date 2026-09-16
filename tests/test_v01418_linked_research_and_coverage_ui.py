from pathlib import Path


APP = Path("app.py").read_text(encoding="utf-8")


def test_release_version_and_analysis_coverage_stages_are_visible():
    assert 'APP_VERSION = "v0.14.35"' in APP
    assert '"Fysiska kortannonser"' in APP
    assert '"Snabbanalyserade"' in APP
    assert '"Djupanalyserade"' in APP


def test_more_analysed_cards_are_available_with_listing_links():
    assert 'Visa fler analyserade kort (' in APP
    assert 'Öppna annonsen på Tradera ↗' in APP


def test_market_gap_rows_render_their_listing_links():
    assert 'for listing in grow.get("listings") or []:' in APP
    assert 'Öppna annonsen – {listing[\'title\']}' in APP
