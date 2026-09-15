from pathlib import Path


APP = Path("app.py").read_text(encoding="utf-8")


def test_release_version_and_partial_seller_search_reopens_panel():
    assert 'APP_VERSION = "v0.14.21"' in APP
    assert '_seller_search_needs_attention = _seller_existing_status in {"INVENTORY_PARTIAL", "PROFILE_INCOMPLETE"}' in APP
    assert 'expanded=_seller_search_needs_attention' in APP


def test_partial_batch_explains_that_search_can_resume_without_restart():
    assert 'Delstopp efter tre profilsidor' in APP
    assert 'Fortsätt söka' in APP
    assert 'utan att börja om' in APP
