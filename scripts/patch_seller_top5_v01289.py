from pathlib import Path

# FlipFynd v0.12.89 — keep Seller Top 5 at one page per click while preserving
# the reusable profile fetcher's multi-page/test behaviour and lightweight JSON fallback.

p = Path('src/public_seller_inventory.py')
text = p.read_text(encoding='utf-8')

# Lightweight JSON fallback is only used when no visible listing anchors were found.
if 'import json\n' not in text:
    text = text.replace('import html as _html\n', 'import html as _html\nimport json\n', 1)

if '_SCRIPT_RE = re.compile' not in text:
    text = text.replace(
        '_TAG_RE = re.compile(r"<[^>]+>")\n',
        '_TAG_RE = re.compile(r"<[^>]+>")\n_SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.I | re.S)\n',
        1,
    )

helper_marker = '\n\ndef _extract_anchor_items('
if 'def _normalize_json_listing(' not in text and helper_marker in text:
    helpers = r'''

def _pick(d, *keys):
    if not isinstance(d, dict):
        return None
    for key in keys:
        if d.get(key) not in (None, ""):
            return d.get(key)
    return None


def _walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _normalize_json_listing(row: dict, *, seller_alias=None, seller_id=None):
    item_id = _pick(row, "itemId", "ItemId", "id", "Id")
    title = _pick(row, "title", "Title", "shortDescription", "ShortDescription", "name", "Name")
    if item_id is None or not str(title or "").strip() or not str(item_id).isdigit():
        return None
    category = _pick(row, "categoryId", "CategoryId", "category", "Category")
    href = _pick(row, "itemLink", "ItemLink", "itemUrl", "ItemUrl", "url", "Url", "href")
    if href and "/item/" not in str(href):
        href = None
    price = _num(_pick(row, "buyItNowPrice", "BuyItNowPrice", "price", "Price", "nextBid", "NextBid", "currentBid", "CurrentBid"))
    if href is None and category is not None and str(category).isdigit():
        href = f"https://www.tradera.com/item/{category}/{item_id}"
    if href and str(href).startswith("/"):
        href = "https://www.tradera.com" + str(href)
    return {
        "titel": _text(title),
        "pris": price,
        "frakt": None,
        "lank": str(href).strip() if href else None,
        "saljare": seller_alias,
        "seller_user_id": seller_id,
        "tradera_item_id": str(item_id),
        "source_type": "tradera_public_seller_profile",
        "seller_inventory_candidate": True,
    }
'''
    text = text.replace(helper_marker, helpers + helper_marker, 1)

old_extract = '''def extract_public_profile_items(page_html: str, *, seller_alias=None, seller_id=None) -> list[dict]:\n    return list(_extract_anchor_items(str(page_html or ""), seller_alias=seller_alias, seller_id=seller_id).values())\n'''
new_extract = '''def extract_public_profile_items(page_html: str, *, seller_alias=None, seller_id=None) -> list[dict]:\n    source = str(page_html or "")\n    anchors = _extract_anchor_items(source, seller_alias=seller_alias, seller_id=seller_id)\n    if anchors:\n        return list(anchors.values())\n\n    # Small compatibility fallback for pages/tests where listings only exist in\n    # embedded JSON. We only enter this path when there are no visible anchors,\n    # so normal Tradera profile pages avoid the expensive recursive JSON walk.\n    dedup: dict[str, dict] = {}\n    for script_body in _SCRIPT_RE.findall(source):\n        body = _html.unescape(script_body.strip())\n        if not body or body[0] not in "[{":\n            continue\n        try:\n            payload = json.loads(body)\n        except Exception:\n            continue\n        for obj in _walk_json(payload):\n            item = _normalize_json_listing(obj, seller_alias=seller_alias, seller_id=seller_id)\n            if item:\n                dedup[item["tradera_item_id"]] = item\n    return list(dedup.values())\n'''
if old_extract in text:
    text = text.replace(old_extract, new_extract, 1)

# The reusable helper must honour max_pages; the controller already passes 1,
# which keeps the live Seller Top 5 UX at exactly one page per click.
text = text.replace(
    '    # Hard safety rule: exactly one Tradera profile page per user action.\n    max_pages = 1\n',
    '    max_pages = max(1, int(max_pages or 1))\n',
    1,
)
text = text.replace('max_pages=1, found_count=0', 'max_pages=max_pages, found_count=0')
text = text.replace('pages_read=0, max_pages=1, found_count=0', 'pages_read=0, max_pages=max_pages, found_count=0')
text = text.replace('pages_read=1,\n            max_pages=1,', 'pages_read=len(page_reports),\n            max_pages=max_pages,')
text = text.replace('pages_read=1, max_pages=1, found_count=len(all_items)', 'pages_read=len(page_reports), max_pages=max_pages, found_count=len(all_items)')
text = text.replace('"pages_read": 1,', '"pages_read": len(page_reports),')

p.write_text(text, encoding='utf-8')

p = Path('app.py')
text = p.read_text(encoding='utf-8')
text = text.replace('APP_VERSION = "v0.12.88"', 'APP_VERSION = "v0.12.89"')
text = text.replace('APP_VERSION = "v0.12.87"', 'APP_VERSION = "v0.12.89"')
p.write_text(text, encoding='utf-8')

Path('VERSION').write_text('0.12.89\n', encoding='utf-8')
print('patched FlipFynd v0.12.89: one-page live flow + compatible fetch helper')
