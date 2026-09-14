from pathlib import Path

# FlipFynd v0.12.86 — one progress indicator + seller name inferred from profile URL.

# 1) Public profile reader: when Tradera redirects /profile/items/<id>/ to
# /profile/items/<id>/<alias>, capture that alias and use it for extracted rows.
p = Path('src/public_seller_inventory.py')
text = p.read_text(encoding='utf-8')
old = '''        response_url = str(getattr(response, "url", None) or url)\n        _remember_paging_suffix(response_url, response.text)\n        total_listing_estimate = None\n'''
new = '''        response_url = str(getattr(response, "url", None) or url)\n        redirected_profile = parse_profile_url(response_url) or {}\n        redirected_alias = str(redirected_profile.get("alias") or "").strip() or None\n        if redirected_alias:\n            effective_alias = redirected_alias\n            parsed["alias"] = redirected_alias\n        _remember_paging_suffix(response_url, response.text)\n        total_listing_estimate = None\n'''
if old in text:
    text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')

# 2) Controller: allow profile-link-only searches. A stable seller-id placeholder is
# used only internally until the redirected Tradera URL reveals the actual alias.
p = Path('src/seller_top5_controller.py')
text = p.read_text(encoding='utf-8')
old = '''    alias = str(seller or "").strip()\n    local_rows = [dict(x) for x in (market_items or []) if isinstance(x, dict)]\n    if not alias:\n        return {"status": "NO_SELLER", "rows": [], "seller": None,\n                "inventory_count": 0, "inventory_source": "NONE", "fallback_reason": None}\n\n    ui = _SellerProgress(enabled=progress_callback is None)\n'''
new = '''    alias = str(seller or "").strip()\n    profile_text = str(profile_url or "").strip()\n    input_profile = parse_profile_url(profile_text) or {}\n    if not alias:\n        alias = str(input_profile.get("alias") or "").strip()\n    if not alias and input_profile.get("seller_id"):\n        alias = f"Tradera #{input_profile.get('seller_id')}"\n    local_rows = [dict(x) for x in (market_items or []) if isinstance(x, dict)]\n    if not alias:\n        return {"status": "NO_SELLER", "rows": [], "seller": None,\n                "inventory_count": 0, "inventory_source": "NONE", "fallback_reason": None}\n\n    ui = _SellerProgress(enabled=False)\n'''
if old in text:
    text = text.replace(old, new, 1)

# profile_text is now initialized above.
text = text.replace('    profile_text = str(profile_url or "").strip()\n    if profile_text:\n', '    if profile_text:\n', 1)

# After every successful public fetch, prefer Tradera's resolved alias for all
# subsequent ranking and display labels.
needle = '''            if not page_result.get("ok"):\n                public_failure = page_result\n                break\n\n            if page_result.get("total_listing_estimate"):\n'''
replacement = '''            if not page_result.get("ok"):\n                public_failure = page_result\n                break\n\n            resolved_alias = str(((page_result.get("seller") or {}).get("alias")) or "").strip()\n            if resolved_alias:\n                alias = resolved_alias\n\n            if page_result.get("total_listing_estimate"):\n'''
if needle in text:
    text = text.replace(needle, replacement, 1)

# Eliminate the controller's internal Streamlit progress bar completely. The app
# owns the single progress indicator via progress_callback.
start = '''class _SellerProgress:\n    \"\"\"Best-effort Streamlit progress UI; inert when an external callback owns UI.\"\"\"\n    def __init__(self, enabled: bool = True):\n        self.bar = None\n        if not enabled:\n            return\n        try:\n            import streamlit as st\n            from streamlit.runtime.scriptrunner import get_script_run_ctx\n            if get_script_run_ctx() is not None:\n                self.bar = st.progress(0, text=\"Steg 1/5 · Hämtar säljarens annonser…\")\n        except Exception:\n            self.bar = None\n'''
replace = '''class _SellerProgress:\n    \"\"\"Compatibility shim. Seller Top 5 renders progress only in app.py.\"\"\"\n    def __init__(self, enabled: bool = True):\n        self.bar = None\n'''
if start in text:
    text = text.replace(start, replace, 1)
p.write_text(text, encoding='utf-8')

# 3) App: seller name is optional when a profile URL is supplied, and version bump.
p = Path('app.py')
text = p.read_text(encoding='utf-8')
text = text.replace('APP_VERSION = "v0.12.85"', 'APP_VERSION = "v0.12.86"')
text = text.replace('seller_top5_alias = st.text_input("Säljare", key="seller_top5_alias", placeholder="t.ex. Etanol71")',
                    'seller_top5_alias = st.text_input("Säljare (valfritt)", key="seller_top5_alias", placeholder="hämtas automatiskt från profillänken")')
old = '''        alias = str(seller_top5_alias or "").strip()\n        if not alias:\n            st.warning("Ange ett säljarnamn först.")\n        else:\n'''
new = '''        alias = str(seller_top5_alias or "").strip()\n        if not alias and not seller_top5_profile_url_resolved:\n            st.warning("Klistra in en Tradera-profillänk eller ange ett säljarnamn.")\n        else:\n'''
if old in text:
    text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')

print('patched FlipFynd v0.12.86: single progress bar + automatic seller identity')
