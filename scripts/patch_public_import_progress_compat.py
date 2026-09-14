from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

# Normalize Tradera's valid ID-only seller profile form in app.py itself so
# mixed Streamlit deploys with an older parser still receive the legacy
# /<seller_id>/<alias> shape they understand.
anchor = '''    seller_top5_sport_label = st.radio(\n        "Sport",\n        ["Hockey", "Fotboll"],\n        horizontal=True,\n        key="seller_top5_sport",\n    )\n'''
insert = anchor + '''    seller_top5_profile_url_resolved = str(seller_top5_profile_url or "").strip()\n    _profile_alias = str(seller_top5_alias or "").strip()\n    if seller_top5_profile_url_resolved and _profile_alias:\n        _profile_base, _profile_sep, _profile_query = seller_top5_profile_url_resolved.partition("?")\n        _profile_clean = _profile_base.rstrip("/")\n        if "/profile/items/" in _profile_clean and _profile_clean.rsplit("/", 1)[-1].isdigit():\n            _profile_base = _profile_clean + "/" + _profile_alias.replace(" ", "%20")\n            seller_top5_profile_url_resolved = _profile_base + ((_profile_sep + _profile_query) if _profile_sep else "")\n'''
if 'seller_top5_profile_url_resolved = str(seller_top5_profile_url or "").strip()' not in text:
    if anchor not in text:
        raise SystemExit("seller profile normalization anchor missing")
    text = text.replace(anchor, insert, 1)

# Use normalized profile URL in Seller Top 5 discovery.
text = text.replace('profile_url=seller_top5_profile_url,', 'profile_url=seller_top5_profile_url_resolved,', 1)

# Use the normalized URL for public inventory import, including compatibility retries.
text = text.replace('elif str(seller_top5_profile_url or "").strip():', 'elif seller_top5_profile_url_resolved:', 1)
text = text.replace('str(seller_top5_profile_url).strip(),', 'seller_top5_profile_url_resolved,')

path.write_text(text, encoding="utf-8")
print("ID-only seller profile URL normalized for current and legacy fetchers")
