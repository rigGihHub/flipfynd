import fetch_data


def test_api_helper_fails_closed_without_credentials():
    out=fetch_data.fetch_tradera_search("McDavid",293316,env={})
    assert out["ok"] is False
    assert out["status"]=="NOT_CONFIGURED"


def test_no_hardcoded_placeholder_secret_remains():
    text=open("fetch_data.py",encoding="utf-8").read()
    assert 'APP_KEY = "BYT_DEN_HÄR_NYCKELN"' not in text
    assert '"searchString"' not in text
    assert '"query"' in text
    assert '"categoryId"' in text
    assert '"orderBy"' in text
