from src.ebay_browse_context import fetch_ebay_active_context


class Response:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


class Session:
    def post(self, *args, **kwargs): return Response({"access_token": "token"})
    def get(self, *args, **kwargs):
        return Response({"itemSummaries": [
            {"title": "Card A", "price": {"value": "6", "currency": "USD"}, "itemWebUrl": "a"},
            {"title": "Card B", "price": {"value": "8", "currency": "USD"}, "itemWebUrl": "b"},
        ]})


def test_browse_context_is_active_only_and_never_sold_evidence():
    out = fetch_ebay_active_context("Leaf Auto /50", client_id="id", client_secret="secret", session=Session())
    assert out["ok"] is True
    assert out["median_usd"] == 7
    assert out["sold_comps"] == 0
    assert out["context_only"] is True


def test_missing_credentials_fails_closed():
    assert fetch_ebay_active_context("card", client_id="", client_secret="")["status"] == "CREDENTIALS_MISSING"
