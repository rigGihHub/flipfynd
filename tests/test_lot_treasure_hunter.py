from src.lot_treasure_hunter import build_lot_treasure_signal, build_lot_treasure_queue


def test_non_lot_is_not_candidate():
    out=build_lot_treasure_signal({})
    assert out["is_lot"] is False
    assert out["candidate"] is False
    assert out["can_create_buy_decision"] is False
    assert out["can_create_market_value"] is False
    assert out["can_allocate_per_card_value"] is False


def test_plain_lot_without_independent_signal_is_not_treasure_candidate():
    out=build_lot_treasure_signal({"is_lot":True,"lot_count":10})
    assert out["is_lot"] is True
    assert out["candidate"] is False


def test_lot_with_information_edge_becomes_manual_review_candidate_only():
    out=build_lot_treasure_signal({
        "is_lot":True,
        "lot_count":12,
        "is_information_edge_candidate":True,
        "information_edge_reasons":["viktiga kortdetaljer saknas i rubriken"],
        "information_edge_verify_first":["kortnummer"],
    })
    assert out["candidate"] is True
    assert out["review_only"] is True
    assert "information-gap" in out["evidence_types"]
    assert out["can_create_buy_decision"] is False


def test_visual_signal_can_prioritise_lot_without_inventing_contents():
    out=build_lot_treasure_signal({
        "is_lot":True,
        "visual_edge_score":70,
    })
    assert out["candidate"] is True
    assert "visual-review" in out["evidence_types"]
    assert "vilka kort som faktiskt ingår" in out["verify_first"]


def test_queue_contains_only_lots_with_extra_evidence():
    q=build_lot_treasure_queue([
        {"titel":"Vanlig lot","is_lot":True,"lot_count":5},
        {"titel":"Kontrollera denna","is_lot":True,"is_hidden_find_candidate":True,
         "hidden_find_reasons":["kort eller generisk rubrik"]},
    ])
    assert [r["title"] for r in q["rows"]]==["Kontrollera denna"]
    assert q["creates_new_decision"] is False
    assert q["creates_new_value"] is False
