from pathlib import Path

# FlipFynd v0.12.90 — robust one-page seller scan.
# Goal: first click must produce visible candidates instead of silently returning
# to the input form when Tradera's HTML shape differs slightly.

p = Path('src/public_seller_inventory.py')
text = p.read_text(encoding='utf-8')

# Add a deliberately broad href matcher. Tradera may append query strings,
# tracking parameters or extra attributes that the older full-anchor regex
# rejected even though the listing link itself was valid.
if '_ITEM_HREF_RE = re.compile' not in text:
    marker = '_PROFILE_RE = re.compile(r"/profile/items/(?P<seller_id>\\d+)(?:/(?P<alias>[^/?#]+))?/?(?:[?#]|$)", re.I)\n'
    insert = marker + '_ITEM_HREF_RE = re.compile(r"href=[\\\"\\\'](?P<href>[^\\\"\\\']*/item/(?P<category>\\d+)/(?P<id>\\d+)[^\\\"\\\']*)[\\\"\\\']", re.I)\n'
    text = text.replace(marker, insert, 1)

start = text.find('def _extract_anchor_items(')
end = text.find('\n\ndef extract_public_profile_items(', start)
if start >= 0 and end > start:
    replacement = r'''def _extract_anchor_items(source: str, *, seller_alias=None, seller_id=None) -> dict[str, dict]:
    """Extract visible Tradera listing links tolerantly.

    Do not depend on one exact <a> serialization. Tradera has changed attribute
    order/query strings several times, which previously made a perfectly valid
    seller page look empty to FlipFynd.
    """
    dedup: dict[str, dict] = {}
    for match in _ITEM_HREF_RE.finditer(source):
        item_id = match.group("id")
        href = _html.unescape(match.group("href") or "")
        if href.startswith("http"):
            absolute_href = href
        else:
            slash = href.find("/item/")
            if slash < 0:
                continue
            absolute_href = "https://www.tradera.com" + href[slash:]

        # Prefer visible anchor text. Limit the search window so embedded JSON
        # cannot be mistaken for a gigantic title.
        a_start = source.rfind("<a", max(0, match.start() - 1200), match.start() + 1)
        if a_start < 0:
            a_start = match.start()
        open_end = source.find(">", match.end())
        close_end = source.find("</a>", max(match.end(), open_end))
        title = ""
        if open_end >= 0 and close_end >= 0 and close_end - open_end < 2500:
            title = _text(source[open_end + 1:close_end])

        # If the anchor is image-only, the human-readable slug is still better
        # than dropping the listing entirely. Embedded JSON remains a separate
        # fallback below and can later replace this with a richer title.
        if not title or len(title) > 350:
            path = absolute_href.split("?", 1)[0].rstrip("/")
            slug = path.rsplit("/", 1)[-1] if "/" in path else ""
            if slug and not slug.isdigit():
                title = _html.unescape(slug.replace("-", " ")).strip()
        if not title:
            title = f"Tradera-annons {item_id}"

        nearby_start = max(0, a_start - 300)
        nearby_end = min(len(source), (close_end + 700) if close_end >= 0 else match.end() + 1200)
        price = _num(_text(source[nearby_start:nearby_end]))
        dedup[item_id] = {
            "titel": title,
            "pris": price,
            "frakt": None,
            "lank": absolute_href,
            "saljare": seller_alias,
            "seller_user_id": seller_id,
            "tradera_item_id": item_id,
            "source_type": "tradera_public_seller_profile",
            "seller_inventory_candidate": True,
        }
    return dedup
'''
    text = text[:start] + replacement + text[end:]

old_headers = 'headers={"User-Agent": "Mozilla/5.0 FlipFynd/1.0", "Accept": "text/html"}'
new_headers = '''headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }'''
text = text.replace(old_headers, new_headers, 1)

# An HTTP 200 without any listing anchors is not proof that the seller inventory
# is exhausted; it can be a bot/challenge/interstitial page. Return an explicit
# retryable failure instead of silently claiming the profile has no cards.
old_empty = '''        if not items:\n            exhausted = True\n            _emit_progress(progress_callback, phase="exhausted", page=page, pages_read=len(page_reports), max_pages=max_pages, found_count=len(all_items), page_count=0, seller_alias=effective_alias)\n            break\n'''
new_empty = '''        if not items:\n            return {\n                "ok": False,\n                "status": "NO_LISTINGS_IN_HTML",\n                "error": "Tradera-sidan svarade men inga annonslänkar kunde läsas ur HTML-svaret.",\n                "items": list(all_items.values()),\n                "next_page": page,\n                "pages_read": len(page_reports),\n                "page_reports": page_reports,\n                "total_listing_estimate": total_listing_estimate,\n            }\n'''
text = text.replace(old_empty, new_empty, 1)

p.write_text(text, encoding='utf-8')

# Make the UI explain a failed/empty public-page fetch instead of appearing to
# do nothing. The main result rendering remains unchanged for successful pages.
p = Path('app.py')
text = p.read_text(encoding='utf-8')
text = text.replace('APP_VERSION = "v0.12.89"', 'APP_VERSION = "v0.12.90"')
needle = '''    elif seller_top5_result and _seller_result_status == "PROFILE_INCOMPLETE":\n        st.caption("Profilen är inte färdigläst ännu. Fortsätt med knappen ovan.")\n'''
insert = needle + '''    if seller_top5_result and not (seller_top5_result.get("rows") or []):\n        _public_status = str(seller_top5_result.get("public_status") or "")\n        _public_error = str(seller_top5_result.get("public_error") or "").strip()\n        if _public_status and _public_status != "OK":\n            st.error(f"Kunde inte läsa annonser från Tradera-profilen ({_public_status}).")\n            if _public_error:\n                st.caption(_public_error)\n            st.caption("Ingen Top 5 visas förrän minst en riktig annons har lästs in.")\n        elif _seller_result_status not in {"PROFILE_INCOMPLETE", "INVENTORY_PARTIAL"}:\n            st.warning("Sökningen gav ännu inga läsbara kortannonser. Försök igen; FlipFynd visar inte en tom körning som ett lyckat resultat.")\n'''
if needle in text and 'Kunde inte läsa annonser från Tradera-profilen' not in text:
    text = text.replace(needle, insert, 1)
p.write_text(text, encoding='utf-8')

Path('VERSION').write_text('0.12.90\n', encoding='utf-8')
print('patched FlipFynd v0.12.90: robust public seller page parser + visible empty-state diagnostics')
