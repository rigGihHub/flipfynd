from src.comp_acquisition_router import build_comp_acquisition_router


IDENTITY = {
    "player_name": "Wayne Gretzky",
    "set_name": "Pinnacle",
    "season": "1995-96",
    "card_number": "101",
}


def sale(source, price):
    return {
        **IDENTITY,
        "source_platform": source,
        "sale_status": "sold",
        "sold": True,
        "source_sale_evidence": "explicit_sold_status",
        "sold_verification_status": "verified",
        "sold_price": price,
        "sold_price_sek": price,
    }


def test_router_prioritises_tradera_when_local_evidence_missing():
    out = build_comp_acquisition_router(IDENTITY, [sale("eBay", 20), sale("eBay", 22)])
    assert out["status"] == "SEARCH_LOCAL"
    assert out["next_source"]["key"] == "tradera_sold"
    assert out["source_quorum"] is False


def test_router_reaches_quorum_with_tradera_and_ebay_exact_sales():
    out = build_comp_acquisition_router(IDENTITY, [sale("Tradera", 18), sale("eBay", 21)])
    assert out["status"] == "SOURCE_QUORUM_REACHED"
    assert out["source_quorum"] is True
    coverage = {row["key"]: row["count"] for row in out["coverage"]}
    assert coverage["tradera"] == 1
    assert coverage["ebay"] == 1


def test_router_blocks_when_identity_is_incomplete():
    out = build_comp_acquisition_router({"player_name": "Wayne Gretzky"}, [])
    assert out["status"] == "IDENTITY_NOT_READY"
    assert out["next_source"] is None
