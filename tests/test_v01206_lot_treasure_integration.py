from pathlib import Path
from src.discovery_engine import build_discovery_map


def test_discovery_marks_lot_treasure_when_independent_signal_exists():
    candidates=[(
        {"pris":100},
        {
            "rank_score":1,
            "player_name":"X",
            "is_lot":True,
            "is_hidden_find_candidate":True,
            "hidden_find_reasons":["kort eller generisk rubrik"],
        },
        {},
    )]
    out=build_discovery_map(candidates)
    assert "lot-research" in out["rows"][0]["tags"]
    assert "lot-treasure" in out["rows"][0]["tags"]


def test_app_imports_bad_listing_and_lot_queue_helpers():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "from src.bad_listing_hunter import build_bad_listing_queue" in app
    assert "from src.lot_treasure_hunter import build_lot_treasure_queue" in app
    assert "Lot Treasure – paket värda kort-för-kort-kontroll" in app
