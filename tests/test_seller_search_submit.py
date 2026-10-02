from pathlib import Path
from unittest.mock import patch
import time
from src import resumable_search

def finish_round(app):
    token = app.query_params["seller_run"]
    if isinstance(token, list): token = token[0]
    for _ in range(200):
        job = resumable_search.load(token)
        if job and job["status"] != "RUNNING":
            break
        time.sleep(.01)
    app.run()
    assert not app.exception


from streamlit.testing.v1 import AppTest


def test_first_submit_uses_both_fresh_fields_and_starts_search():
    result = {"status": "OK", "inventory_count": 0, "rows": []}
    with patch("src.seller_top5_controller.resolve_seller_top5", return_value=result) as search, \
            patch("importlib.reload", side_effect=lambda module: module):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
        app.text_input(key="seller_top5_alias").set_value("CarolinaHKY")
        app.text_input(key="seller_top5_profile_url").set_value(
            "https://www.tradera.com/profile/items/216047/"
        )
        app.button(key="seller_top5_run").click().run()

        assert not app.exception
        finish_round(app)
        search.assert_called_once()
        assert search.call_args.args[0] == "CarolinaHKY"
        assert search.call_args.kwargs["profile_url"] == (
            "https://www.tradera.com/profile/items/216047/CarolinaHKY"
        )
        assert app.session_state["seller_top5_result"] == result
        assert app.session_state["_applied_seller_run"] == (app.query_params["seller_run"][0] if isinstance(app.query_params["seller_run"], list) else app.query_params["seller_run"])
        app.run()
        search.assert_called_once()


def test_empty_submit_reports_validation_without_starting_search():
    with patch("src.seller_top5_controller.resolve_seller_top5") as search:
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
        app.button(key="seller_top5_run").click().run()
        assert not app.exception
        search.assert_not_called()
        assert any("Klistra in en Tradera-profillänk" in warning.value for warning in app.warning)


def test_submit_survives_browser_backup_restoration_rerun():
    """The device's saved main search must not swallow a seller submission."""
    reply = {"value": None}
    restored = {"snapshot": None}
    original_load = resumable_search.load

    def recover(*args):
        restored["snapshot"] = {"status": "INTERRUPTED", "params": {}}
        return True

    result = {"status": "OK", "inventory_count": 0, "rows": []}
    with patch("src.seller_top5_controller.resolve_seller_top5", return_value=result) as search, \
            patch("importlib.reload", side_effect=lambda module: module), \
            patch("src.browser_search_backup.browser_backup", side_effect=lambda *a, **k: reply["value"]), \
            patch("src.browser_search_backup.recover_browser_search", side_effect=recover), \
            patch("src.resumable_search.load", side_effect=lambda token, *a, **k: restored["snapshot"] if token == "a" * 32 else original_load(token, *a, **k)):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
        app.text_input(key="seller_top5_alias").set_value("CarolinaHKY")
        app.text_input(key="seller_top5_profile_url").set_value(
            "https://www.tradera.com/profile/items/216047/"
        )
        reply["value"] = {"token": "a" * 32, "blob": "saved-device-search"}
        app.button(key="seller_top5_run").click().run()
        assert not app.exception
        finish_round(app)
        search.assert_called_once()
        assert app.session_state["seller_top5_result"] == result
        app.run()
        search.assert_called_once()
