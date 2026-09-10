from src.external_sold_sources import adapt_external_rows
from src.sold_comp_import import normalize_sold_comp
from src.sold_comp_intake import review_sold_comp_intake


def test_external_adapter_preserves_explicit_identity_fields():
    rows = [{
        "title": "Player Set #10",
        "price": 125,
        "currency": "SEK",
        "status": "sold",
        "player": "Player",
        "set": "Set",
        "year": "2025-26",
        "card_no": "10",
        "identity_verified": True,
        "identity_source": "source_export",
    }]
    adapted = adapt_external_rows(rows, "generic")
    assert adapted["adapted_count"] == 1
    row = adapted["rows"][0]
    assert row["player_name"] == "Player"
    assert row["set_name"] == "Set"
    assert row["season"] == "2025-26"
    assert row["card_number"] == "10"
    assert row["identity_verified"] is True


def test_preserved_identity_can_become_exact_ready_after_strict_normalization():
    source = {
        "title": "Player Set #10",
        "price": 125,
        "currency": "SEK",
        "status": "sold",
        "player": "Player",
        "set": "Set",
        "year": "2025-26",
        "card_no": "10",
        "identity_verified": True,
        "identity_source": "source_export",
    }
    adapted = adapt_external_rows([source], "generic")["rows"][0]
    record = normalize_sold_comp(adapted, provenance="test")
    review = review_sold_comp_intake(record)
    assert review["sale_verified"] is True
    assert review["exact_identity_ready"] is True
