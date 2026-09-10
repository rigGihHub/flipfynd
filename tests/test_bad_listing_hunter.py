from src.bad_listing_hunter import build_bad_listing_signal, build_bad_listing_queue


def test_no_signal_is_not_candidate():
    out=build_bad_listing_signal({})
    assert out["candidate"] is False
    assert out["can_create_identity"] is False
    assert out["can_create_market_value"] is False
    assert out["can_create_buy_decision"] is False


def test_missing_identity_fields_create_review_traits_not_facts():
    out=build_bad_listing_signal({
        "listing_quality_score":45,
        "listing_quality_warnings":[
            "set/program saknas eller är otydligt",
            "kortnummer saknas",
        ],
    })
    assert out["candidate"] is True
    assert "missing-set" in out["traits"]
    assert "missing-card-number" in out["traits"]
    assert out["review_only"] is True


def test_identity_conflict_is_candidate_but_not_corrected():
    out=build_bad_listing_signal({
        "listing_quality_blockers":["motstridig kortinformation mellan titel och annonsinfo"],
    })
    assert out["candidate"] is True
    assert "identity-conflict" in out["traits"]
    assert out["can_create_identity"] is False


def test_hidden_and_information_edge_reused():
    out=build_bad_listing_signal({
        "is_hidden_find_candidate":True,
        "hidden_find_reasons":["kort eller generisk rubrik"],
        "is_information_edge_candidate":True,
        "information_edge_reasons":["annonsinformationen innehåller viktigare kortdetaljer än rubriken"],
        "information_edge_verify_first":["kortnummer"],
    })
    assert out["candidate"] is True
    assert "underexposed" in out["traits"]
    assert "information-gap" in out["traits"]


def test_queue_only_contains_candidates():
    q=build_bad_listing_queue([
        {"titel":"Bra annons"},
        {"titel":"Svag annons","listing_quality_score":40,
         "listing_quality_warnings":["kortnummer saknas","set/program saknas eller är otydligt"]},
    ])
    assert [r["title"] for r in q["rows"]]==["Svag annons"]
    assert q["creates_new_decision"] is False
