from src.comp_source_diversity import build_comp_source_diversity

def row(source=None, seller=None, ident=None):
    r={
        "player_name":"P","season":"2025","set_name":"Set","card_number":"1",
        "sold_price":100,"sold_at":"2026-08-01",
        "sold_comp_id": ident or f"{source}-{seller}",
    }
    if source is not None: r["source_platform"]=source
    if seller is not None: r["saljare"]=seller
    return r

def test_multiple_marketplaces_are_reported():
    r=build_comp_source_diversity([row("eBay","A","1"),row("Tradera","B","2"),row("eBay","C","3")])
    assert r["marketplaces"]["unique_count"]==2
    assert r["marketplaces"]["counts"]["eBay"]==2

def test_single_marketplace_is_concentrated():
    r=build_comp_source_diversity([row("eBay","A","1"),row("eBay","B","2"),row("eBay","C","3")])
    assert r["status"]=="CONCENTRATED"
    assert any("samma marknadsplats" in w for w in r["warnings"])

def test_single_seller_with_multiple_sales_is_flagged():
    r=build_comp_source_diversity([row("eBay","Same","1"),row("Tradera","Same","2")])
    assert r["sellers"]["status"]=="SINGLE"
    assert any("samma säljare" in w for w in r["warnings"])

def test_missing_source_is_not_invented():
    r=build_comp_source_diversity([row(None,"A","1"),row("eBay","B","2")])
    assert r["marketplaces"]["missing_count"]==1
    assert r["marketplaces"]["unique_count"]==1

def test_no_rows_abstains():
    assert build_comp_source_diversity([])["status"]=="NO_EXACT_COMPS"

def test_duplicates_are_collapsed_before_diversity():
    a=row("eBay","A","same")
    b=dict(a)
    r=build_comp_source_diversity([a,b,row("Tradera","B","other")])
    assert r["independent_count"]==2
    assert r["marketplaces"]["unique_count"]==2
