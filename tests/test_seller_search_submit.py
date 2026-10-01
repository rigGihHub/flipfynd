from pathlib import Path
from unittest.mock import patch

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
        search.assert_called_once()
        assert search.call_args.args[0] == "CarolinaHKY"
        assert search.call_args.kwargs["profile_url"] == (
            "https://www.tradera.com/profile/items/216047/CarolinaHKY"
        )
        assert app.session_state["seller_top5_result"] == result
        assert any(status.state == "complete" for status in app.status)


def test_empty_submit_reports_validation_without_starting_search():
    with patch("src.seller_top5_controller.resolve_seller_top5") as search:
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
        app.button(key="seller_top5_run").click().run()
        assert not app.exception
        search.assert_not_called()
        assert any("Klistra in en Tradera-profillänk" in warning.value for warning in app.warning)
