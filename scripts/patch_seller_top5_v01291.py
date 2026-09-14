from pathlib import Path

controller = Path('src/seller_top5_controller.py')
text = controller.read_text(encoding='utf-8')

import_line = 'from src.public_seller_inventory import fetch_public_seller_inventory_batch, parse_profile_url\n'
proxy_import = import_line + 'from src.seller_proxy_inventory import fetch_proxy_seller_inventory_batch\n'
if 'from src.seller_proxy_inventory import fetch_proxy_seller_inventory_batch' not in text:
    if import_line not in text:
        raise SystemExit('public seller inventory import not found')
    text = text.replace(import_line, proxy_import, 1)

old = '''            if not page_result.get("ok"):\n                public_failure = page_result\n                break\n'''
new = '''            if not page_result.get("ok"):\n                # Streamlit Cloud can be blocked/reset by Tradera even when the\n                # public profile is healthy. Retry the same single page through\n                # the dedicated browser-like Render fetcher before giving up.\n                try:\n                    proxy_result = fetch_proxy_seller_inventory_batch(\n                        profile_text,\n                        start_page=current_page,\n                        max_pages=1,\n                        progress_callback=combined_progress,\n                        fallback_alias=alias,\n                    )\n                except Exception as exc:\n                    proxy_result = {\n                        "ok": False,\n                        "status": "PROXY_FETCH_EXCEPTION",\n                        "error": str(exc),\n                        "items": [],\n                        "next_page": current_page,\n                    }\n                if proxy_result.get("ok"):\n                    page_result = proxy_result\n                else:\n                    page_result = dict(page_result)\n                    page_result["direct_fetch_error"] = page_result.get("error")\n                    page_result["proxy_status"] = proxy_result.get("status")\n                    page_result["proxy_error"] = proxy_result.get("error")\n\n            if not page_result.get("ok"):\n                public_failure = page_result\n                break\n'''
if old not in text:
    if 'proxy_result = fetch_proxy_seller_inventory_batch' not in text:
        raise SystemExit('public failure block not found')
else:
    text = text.replace(old, new, 1)

controller.write_text(text, encoding='utf-8')

app = Path('app.py')
app_text = app.read_text(encoding='utf-8')
app_text = app_text.replace('APP_VERSION = "v0.12.90"', 'APP_VERSION = "v0.12.91"')
# Surface both direct and proxy causes so the UI never returns a mystery FETCH_EXCEPTION again.
needle = 'st.error(f"Kunde inte läsa annonser från Tradera-profilen ({_seller_result_status}).")'
replacement = '''st.error(f"Kunde inte läsa annonser från Tradera-profilen ({_seller_result_status}).")\n        _public_error = seller_top5_result.get("public_error")\n        _proxy_status = seller_top5_result.get("proxy_status")\n        _proxy_error = seller_top5_result.get("proxy_error")\n        if _public_error:\n            st.caption(f"Direkt hämtning: {_public_error}")\n        if _proxy_status or _proxy_error:\n            st.caption(f"Reservhämtning: {_proxy_status or 'fel'}" + (f" · {_proxy_error}" if _proxy_error else ""))'''
if needle in app_text and '_proxy_status = seller_top5_result.get("proxy_status")' not in app_text:
    app_text = app_text.replace(needle, replacement, 1)
app.write_text(app_text, encoding='utf-8')

version = Path('VERSION')
if version.exists():
    version.write_text('0.12.91\n', encoding='utf-8')
