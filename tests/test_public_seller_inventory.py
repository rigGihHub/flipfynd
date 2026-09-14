from src.public_seller_inventory import (
    build_profile_page_url,
    extract_public_profile_items,
    fetch_public_seller_inventory_batch,
    parse_profile_url,
)


def test_parse_profile_url():
    parsed = parse_profile_url("https://www.tradera.com/profile/items/5412219/etanol71?paging=3.a0.s7726")
    assert parsed == {"seller_id": "5412219", "alias": "etanol71"}


def test_build_profile_page_url_preserves_paging_suffix():
    url = build_profile_page_url("https://www.tradera.com/profile/items/5412219/etanol71?paging=3.a0.s7726", 8)
    assert "paging=8.a0.s7726" in url


def test_extract_embedded_json_listing():
    html = '''
    <html><body>
    <script type="application/json">
    {"props":{"items":[{"itemId":745296382,"title":"2020 UEFA Euro Panini #409","buyItNowPrice":30,"categoryId":293311,"itemUrl":"/item/293311/745296382/test"}]}}
    </script>
    </body></html>
    '''
    items = extract_public_profile_items(html, seller_alias="Etanol71", seller_id="5412219")
    assert len(items) == 1
    row = items[0]
    assert row["tradera_item_id"] == "745296382"
    assert row["titel"] == "2020 UEFA Euro Panini #409"
    assert row["pris"] == 30.0
    assert row["saljare"] == "Etanol71"
    assert row["seller_user_id"] == "5412219"
    assert row["source_type"] == "tradera_public_seller_profile"


def test_extract_anchor_fallback_listing():
    html = '''
    <div class="card">
      <a href="/item/293316/123456789/upper-deck-young-guns">Upper Deck Young Guns #201</a>
      <span>Pris: 75 kr, Köp nu.</span>
    </div>
    '''
    items = extract_public_profile_items(html, seller_alias="SellerX", seller_id="99")
    assert len(items) == 1
    assert items[0]["tradera_item_id"] == "123456789"
    assert items[0]["pris"] == 75.0


class _Response:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class _Session:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = 0

    def get(self, url, headers=None, timeout=None):
        idx = min(self.calls, len(self.pages) - 1)
        self.calls += 1
        return _Response(self.pages[idx])


def test_batch_stops_on_repeated_page():
    page = '<a href="/item/293311/111/test">Card A</a><span>20 kr</span>'
    session = _Session([page, page])
    result = fetch_public_seller_inventory_batch(
        "https://www.tradera.com/profile/items/5412219/etanol71?paging=1.a0.s7726",
        start_page=1,
        max_pages=10,
        session=session,
    )
    assert result["ok"] is True
    assert result["parsed_count"] == 1
    assert result["exhausted"] is True
    assert result["pages_read"] == 2
