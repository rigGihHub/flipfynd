from src.oddity_registry_learning import build_registry_proposal_queue


def _item(title, *, sold=0, groups=0, exact=False, checklist=False, url="https://example.test/1"):
    return {
        "title": title,
        "sport": "hockey",
        "player_name": "Example Player",
        "season": "1995-96",
        "set_name": "Example Set",
        "card_number": "77",
        "nonstandard_value_signals": [{"category":"IMAGE_VARIATION","type":"Bildvariant","reason":"möjlig variant"}],
        "exact_identity_verified": exact,
        "exact_sold_comps": sold,
        "sold_source_groups": groups,
        "checklist_verified": checklist,
        "url": url,
    }


def test_repeated_evidence_rich_candidate_becomes_review_ready():
    q=build_registry_proposal_queue([
        _item("1995-96 Example Set #77 Example Player variation", sold=2, groups=2, exact=True, checklist=True, url="https://x/1"),
        _item("Example Player 1995-96 Example Set 77 photo variation", sold=1, groups=1, exact=True, url="https://x/2"),
    ])
    assert q["review_ready_count"] == 1
    row=q["rows"][0]
    assert row["status"] == "REVIEW_READY"
    assert row["auto_add_allowed"] is False
    assert row["creates_market_value"] is False


def test_single_listing_never_auto_promotes():
    q=build_registry_proposal_queue([_item("single oddity", sold=8, groups=3, exact=True, checklist=True)])
    assert q["review_ready_count"] == 0
    assert q["rows"][0]["status"] == "NEEDS_EVIDENCE"


def test_no_oddity_signal_means_no_proposal():
    item=_item("ordinary card")
    item["nonstandard_value_signals"]=[]
    q=build_registry_proposal_queue([item,item.copy()])
    assert q["rows"] == []


def test_existing_curated_card_is_excluded():
    item={
        "title":"1990-91 Hoops #205 Mark Jackson",
        "sport":"basketball",
        "player_name":"Mark Jackson",
        "season":"1990-91",
        "set_name":"Hoops",
        "card_number":"205",
        "nonstandard_value_signals":[{"category":"BACKGROUND_STORY"}],
        "exact_identity_verified":True,
        "exact_sold_comps":4,
    }
    q=build_registry_proposal_queue([item,item.copy()])
    assert q["rows"] == []
