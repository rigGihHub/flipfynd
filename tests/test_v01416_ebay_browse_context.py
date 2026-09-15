from src.ebay_browse_context import fetch_ebay_active_context


class Response:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


class Session:
    def post(self, *args, **kwargs): return Response({"access_token": "token"})
    def get(self, *args, **kwargs):
        return Response({"itemSummaries": [
            {"title": "2021-22 Leaf Memories #BG-EA1 Emmanuel Akot Auto /50", "price": {"value": "6", "currency": "USD"}, "itemWebUrl": "a"},
            {"title": "2021-22 Leaf Memories #BG-EA1 Emmanuel Akot Auto /50", "price": {"value": "8", "currency": "USD"}, "itemWebUrl": "b"},
            {"title": "2022-23 Leaf Memories #BG-EA2 Wrong Player Base", "price": {"value": "99", "currency": "USD"}, "itemWebUrl": "wrong"},
        ]})


IDENTITY = {"player_name": "Emmanuel Akot", "season": "2021-22", "set_name": "Leaf Memories", "card_number": "BG-EA1", "is_auto": True, "serial_denominator": "50"}


def test_browse_context_is_active_only_and_never_sold_evidence():
    out = fetch_ebay_active_context("Leaf Auto /50", identity=IDENTITY, client_id="id", client_secret="secret", session=Session())
    assert out["ok"] is True
    assert out["median_usd"] == 7
    assert out["sold_comps"] == 0
    assert out["context_only"] is True
    assert out["raw_listing_count"] == 3
    assert out["rejected_listing_count"] == 1


def test_missing_credentials_fails_closed():
    assert fetch_ebay_active_context("card", client_id="", client_secret="")["status"] == "CREDENTIALS_MISSING"
