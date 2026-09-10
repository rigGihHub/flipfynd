from pathlib import Path
from src.discovery_engine import build_discovery_map


def test_bad_listing_can_enter_discovery_via_existing_quality_evidence():
    candidates=[(
        {"pris":50},
        {
            "rank_score":1,
            "player_name":"X",
            "listing_quality_score":40,
            "listing_quality_warnings":["kortnummer saknas","set/program saknas eller är otydligt"],
        },
        {},
    )]
    out=build_discovery_map(candidates)
    assert "bad-listing" in out["rows"][0]["tags"]


def test_ui_explains_bad_listing_is_not_card_fact():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "Dåligt beskrivna annonser – kan vara lättare att missa" in app
    assert "inte kortfakta eller nya KÖP" in app
