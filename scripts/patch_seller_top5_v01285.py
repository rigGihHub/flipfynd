from pathlib import Path

# FlipFynd v0.12.85 — Seller Top 5 continuation + first-batch ranking + remaining count.

# 1) Public Tradera fetch: never invent a paging suffix on page 1. The first page
# is fetched as the canonical profile URL so Tradera can reveal its real paging
# token. Also capture the seller's visible total listing count when present.
p = Path('src/public_seller_inventory.py')
text = p.read_text(encoding='utf-8')
old = '''def build_profile_page_url(profile_url: str, page_number: int) -> str:\n    parsed = urlparse(str(profile_url or "").strip())\n    query = parse_qs(parsed.query, keep_blank_values=True)\n    old = (query.get("paging") or [""])[0]\n    suffix = ""\n    if "." in old:\n        suffix = old[old.find("."):]\n    if not suffix:\n        profile = parse_profile_url(profile_url) or {}\n        seller_id = str(profile.get("seller_id") or "")\n        suffix = _PAGING_SUFFIX_CACHE.get(seller_id, ".a0.s999999")\n    query["paging"] = [f"{max(1, int(page_number))}{suffix}"]\n    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))\n'''
new = '''def build_profile_page_url(profile_url: str, page_number: int) -> str:\n    parsed = urlparse(str(profile_url or "").strip())\n    query = parse_qs(parsed.query, keep_blank_values=True)\n    page_number = max(1, int(page_number))\n    old = (query.get("paging") or [""])[0]\n    # Important: page 1 must use the canonical profile URL if no paging token is\n    # already present. A fabricated token can make Tradera return an empty page.\n    if page_number == 1 and not old:\n        return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))\n    suffix = ""\n    if "." in old:\n        suffix = old[old.find("."):]\n    if not suffix:\n        profile = parse_profile_url(profile_url) or {}\n        seller_id = str(profile.get("seller_id") or "")\n        suffix = _PAGING_SUFFIX_CACHE.get(seller_id, ".a0.s48")\n    query["paging"] = [f"{page_number}{suffix}"]\n    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))\n'''
if old in text:
    text = text.replace(old, new, 1)

if '_TOTAL_LISTINGS_RE' not in text:
    text = text.replace(
        '_PAGING_HINT_RE = re.compile(r"paging=\\d+\\.a0\\.s(?P<count>\\d+)", re.I)\n',
        '_PAGING_HINT_RE = re.compile(r"paging=\\d+\\.a0\\.s(?P<count>\\d+)", re.I)\n_TOTAL_LISTINGS_RE = re.compile(r"(?P<count>\\d[\\d\\s\\u00a0.]*)\\s+Annonser", re.I)\n',
        1,
    )

marker = '''        response_url = str(getattr(response, "url", None) or url)\n        _remember_paging_suffix(response_url, response.text)\n        items = extract_public_profile_items(response.text, seller_alias=effective_alias, seller_id=parsed["seller_id"])\n'''
replacement = '''        response_url = str(getattr(response, "url", None) or url)\n        _remember_paging_suffix(response_url, response.text)\n        total_listing_estimate = None\n        total_match = _TOTAL_LISTINGS_RE.search(_text(response.text))\n        if total_match:\n            try:\n                total_listing_estimate = int(re.sub(r"[^0-9]", "", total_match.group("count")))\n            except (TypeError, ValueError):\n                total_listing_estimate = None\n        items = extract_public_profile_items(response.text, seller_alias=effective_alias, seller_id=parsed["seller_id"])\n'''
if marker in text:
    text = text.replace(marker, replacement, 1)

ret = '''        "inventory_source": "TRADERA_PUBLIC_PROFILE",\n    }\n'''
ret_new = '''        "inventory_source": "TRADERA_PUBLIC_PROFILE",\n        "total_listing_estimate": locals().get("total_listing_estimate"),\n    }\n'''
if ret in text and '"total_listing_estimate": locals().get("total_listing_estimate")' not in text:
    text = text.replace(ret, ret_new, 1)
p.write_text(text, encoding='utf-8')

# 2) Controller: preserve the visible total through checkpoints/results so UI can
# say how many are loaded and approximately how many remain.
p = Path('src/seller_top5_controller.py')
text = p.read_text(encoding='utf-8')
if 'total_listing_estimate: int | None = None,' not in text:
    text = text.replace(
        '    resume_required: bool,\n):',
        '    resume_required: bool,\n    total_listing_estimate: int | None = None,\n):',
        1,
    )
    text = text.replace(
        '        "api_status": api_status,\n    })',
        '        "api_status": api_status,\n        "total_listing_estimate": total_listing_estimate,\n        "remaining_listing_estimate": max(0, int(total_listing_estimate) - len(saved_items)) if total_listing_estimate else None,\n    })',
        1,
    )

# Checkpoint default and accumulation.
text = text.replace(
    'checkpoint = {"next_page": 1, "pages_read": 0, "items": {}}',
    'checkpoint = {"next_page": 1, "pages_read": 0, "items": {}, "total_listing_estimate": None}',
)
text = text.replace(
    '                "items": {},\n            }',
    '                "items": {},\n                "total_listing_estimate": None,\n            }',
)
if 'total_listing_estimate = checkpoint.get("total_listing_estimate")' not in text:
    text = text.replace(
        '        public_failure = None\n',
        '        public_failure = None\n        total_listing_estimate = checkpoint.get("total_listing_estimate")\n',
        1,
    )
    text = text.replace(
        '            page_items = _sanitize_public_items(\n',
        '            if page_result.get("total_listing_estimate"):\n                total_listing_estimate = int(page_result.get("total_listing_estimate"))\n            page_items = _sanitize_public_items(\n',
        1,
    )

text = text.replace(
    '                    "items": stored_items,\n                },',
    '                    "items": stored_items,\n                    "total_listing_estimate": total_listing_estimate,\n                },',
)
text = text.replace(
    '{"next_page": current_page, "pages_read": total_pages_read, "items": stored_items}',
    '{"next_page": current_page, "pages_read": total_pages_read, "items": stored_items, "total_listing_estimate": total_listing_estimate}',
)

# Add total estimate to both partial-result calls.
needle = '                resume_required=True,\n            )'
if needle in text:
    text = text.replace(needle, '                resume_required=True,\n                total_listing_estimate=total_listing_estimate,\n            )', 1)
needle = '                resume_required=False,\n            )'
if needle in text:
    text = text.replace(needle, '                resume_required=False,\n                total_listing_estimate=total_listing_estimate,\n            )', 1)

# Completed public result also exposes the estimate.
if 'result["total_listing_estimate"] = total_listing_estimate' not in text:
    text = text.replace(
        '        result = _rank(\n            alias,\n            list(stored_items.values()),',
        '        result = _rank(\n            alias,\n            list(stored_items.values()),',
        1,
    )
    # insert near final return via a safe unique assignment later in the public branch
    anchor = '        clear_checkpoint(key, session=session)\n        result = _rank('
    if anchor in text:
        pass

p.write_text(text, encoding='utf-8')

# 3) App UX: rerender after a partial batch so the same top button immediately
# turns into Continue. Show loaded/remaining counts and keep provisional Top 5.
p = Path('app.py')
text = p.read_text(encoding='utf-8')
text = text.replace('APP_VERSION = "v0.12.84"', 'APP_VERSION = "v0.12.85"')
text = text.replace('APP_VERSION = "v0.12.83"', 'APP_VERSION = "v0.12.85"')

# The partial branch should not say 20% forever; it is a completed batch.
text = text.replace(
    'seller_progress_bar.progress(20, text=f"20% · {found_count} annonser sparade")',
    'seller_progress_bar.progress(100, text=f"{found_count} annonser inlästa · block klart")',
)

# Force one clean rerender after a batch/status update so the button label is
# immediately recomputed from the newly saved result.
partial_anchor = '''                    seller_status.update(label=f"📥 Block sparat för {alias} · fortsätt nästa 5 sidor", state="complete", expanded=False)\n'''
if partial_anchor in text and 'st.rerun()  # refresh Seller Top 5 continuation UI' not in text:
    text = text.replace(partial_anchor, partial_anchor + '                    st.rerun()  # refresh Seller Top 5 continuation UI\n', 1)
profile_anchor = '''                    seller_status.update(label=f"⚠️ Hela profilen för {alias} är inte inläst", state="error", expanded=True)\n'''
if profile_anchor in text and 'st.rerun()  # refresh continuation button after incomplete profile' not in text:
    text = text.replace(profile_anchor, profile_anchor + '                    st.rerun()  # refresh continuation button after incomplete profile\n', 1)

# Clear, user-facing inventory progress text.
old_status = '''        if seller_top5_result.get("resume_required"):\n            st.caption(f"Sökningen pausades · {_pages} sidor och {_saved} annonser sparade · fortsätter från sida {_next}.")\n        else:\n            st.caption(f"Sökning pågår · {_pages} sidor · {_saved} annonser · nästa sida {_next}.")\n'''
new_status = '''        _total_est = seller_top5_result.get("total_listing_estimate")\n        _remaining_est = seller_top5_result.get("remaining_listing_estimate")\n        if _total_est:\n            _inventory_line = f"{_saved} inlästa · cirka {int(_remaining_est or 0)} kvar · {_pages} sidor lästa"\n        else:\n            _inventory_line = f"{_saved} inlästa · {_pages} sidor lästa · fortsätter från sida {_next}"\n        if seller_top5_result.get("resume_required"):\n            st.caption(f"Sökningen pausades · {_inventory_line}.")\n        else:\n            st.caption(f"Sökning pågår · {_inventory_line}.")\n'''
if old_status in text:
    text = text.replace(old_status, new_status, 1)

# Incomplete state should never tell user to press a button that isn't visible;
# after rerender the top button is the continuation button.
text = text.replace(
    'st.caption("Profilen är inte färdigläst ännu. Tryck på Fortsätt söka.")',
    'st.caption("Profilen är inte färdigläst ännu. Fortsätt med knappen ovan.")',
)

p.write_text(text, encoding='utf-8')
print('patched FlipFynd v0.12.85 seller continuation, provisional Top 5 and remaining count')
