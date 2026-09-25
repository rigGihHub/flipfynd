from seller_fetch_proxy import (
    _PAGE_URL_CACHE, _cache_key, _is_exhausted_page, _page_href,
    _safe_tradera_page_url,
)


def test_real_tradera_paging_token_is_extracted():
    html = '<a aria-label="Sida 10" href="/profile/items/123/foo?paging=10.a0.s9529">10</a>'
    assert _page_href(html, 10) == "/profile/items/123/foo?paging=10.a0.s9529"


def test_page_cursor_cache_distinguishes_seller_alias_and_page():
    _PAGE_URL_CACHE.clear()
    key10 = _cache_key(123, "Etanol71", 10)
    key11 = _cache_key(123, "Etanol71", 11)
    _PAGE_URL_CACHE[key10] = "https://www.tradera.com/profile/items/123/Etanol71?paging=10.a0.s9529"
    assert _PAGE_URL_CACHE[key10].endswith("paging=10.a0.s9529")
    assert key11 not in _PAGE_URL_CACHE


def test_only_tradera_profile_urls_are_accepted_as_cached_cursors():
    assert _safe_tradera_page_url("https://www.tradera.com/profile/items/123/foo?paging=11.a0.s9529")
    assert not _safe_tradera_page_url("https://evil.example/profile/items/123/foo?paging=11.a0.s9529")
    assert not _safe_tradera_page_url("https://www.tradera.com/item/123/456")


def test_partial_final_page_without_next_link_is_normal_end():
    html = "<h1>208 Annonser</h1>" + "<article></article>" * 48
    assert _is_exhausted_page(html, page=3, item_count=48) is True


def test_missing_next_link_on_full_nonfinal_page_is_not_silently_end():
    html = "<h1>9000 Annonser</h1>" + "<article></article>" * 80
    assert _is_exhausted_page(html, page=3, item_count=80) is False


def test_real_next_link_overrides_partial_page_shape():
    html = '<h1>208 Annonser</h1><a aria-label="Sida 4" href="?paging=4.a0.s208">4</a>'
    assert _is_exhausted_page(html, page=3, item_count=48) is False
