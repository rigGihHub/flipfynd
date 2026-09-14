from pathlib import Path

# Keep Seller Top 5 responsive while inventory is checkpointed in 10-page blocks.
# Partial blocks get a lightweight provisional ranking; the completed inventory
# gets a deeper 30-candidate full analysis.

controller = Path('src/seller_top5_controller.py')
text = controller.read_text(encoding='utf-8')
original = text

old_partial = '''            if not exhausted:\n                if session is not None:\n                    session[key] = {\n                        "next_page": next_page,\n                        "pages_read": total_pages_read,\n                        "items": stored_items,\n                    }\n                return {\n                    "status": "INVENTORY_PARTIAL",\n                    "seller": alias,\n                    "rows": [],\n                    "inventory_count": len(stored_items),\n                    "inventory_source": "TRADERA_PUBLIC_PROFILE",\n                    "public_status": public.get("status") or "OK",\n                    "public_pages_read": total_pages_read,\n                    "public_next_page": next_page,\n                    "public_batch_pages": int(public.get("pages_read") or 0),\n                    "public_inventory_complete": False,\n                    "fallback_reason": "NO_API_CREDENTIALS" if not creds else "API_FAILED",\n                    "api_status": (api_failure or {}).get("status") if api_failure else ("NOT_CONFIGURED" if not creds else "OK"),\n                }\n'''

new_partial = '''            if not exhausted:\n                if session is not None:\n                    session[key] = {\n                        "next_page": next_page,\n                        "pages_read": total_pages_read,\n                        "items": stored_items,\n                    }\n                # Show a living provisional Top 5 after every 10-page block. Keep\n                # this preview deliberately lighter than the final pass so a\n                # checkpoint remains fast and robust on Streamlit Cloud.\n                preview = _rank(\n                    alias,\n                    list(stored_items.values()),\n                    analyze_fn=analyze_fn,\n                    quick_limit=quick_limit,\n                    full_limit=min(5, max(1, int(full_limit or 5))),\n                    source="TRADERA_PUBLIC_PROFILE",\n                    progress_callback=progress_callback,\n                    ui=ui,\n                )\n                preview = dict(preview)\n                preview.update({\n                    "status": "INVENTORY_PARTIAL",\n                    "inventory_count": len(stored_items),\n                    "inventory_source": "TRADERA_PUBLIC_PROFILE",\n                    "public_status": public.get("status") or "OK",\n                    "public_pages_read": total_pages_read,\n                    "public_next_page": next_page,\n                    "public_batch_pages": int(public.get("pages_read") or 0),\n                    "public_inventory_complete": False,\n                    "provisional_top5": True,\n                    "fallback_reason": "NO_API_CREDENTIALS" if not creds else "API_FAILED",\n                    "api_status": (api_failure or {}).get("status") if api_failure else ("NOT_CONFIGURED" if not creds else "OK"),\n                })\n                return preview\n'''

if old_partial in text:
    text = text.replace(old_partial, new_partial, 1)
elif '"provisional_top5": True' not in text:
    raise SystemExit('controller partial checkpoint block not found')

if text != original:
    controller.write_text(text, encoding='utf-8')

app = Path('app.py')
text = app.read_text(encoding='utf-8')
original = text

# Final completed inventory: full-analyse 30 strongest candidates.
text = text.replace('                        full_limit=10,', '                        full_limit=30,')

old_info = '''        st.info(f"📥 Inventering pågår: {_pages} profilsidor lästa och {_saved} unika annonser sparade. Nästa block börjar på sida {_next}. Tryck på ‘Fortsätt läsa nästa 10 sidor’. Top 5 rankas först när hela profilen är inläst.")'''
new_info = '''        st.info(f"📥 Inventering pågår: {_pages} profilsidor lästa och {_saved} unika annonser sparade. Nästa block börjar på sida {_next}. Preliminär Top 5 uppdateras löpande; tryck på ‘Fortsätt läsa nästa 10 sidor’.")'''
text = text.replace(old_info, new_info)

old_gate = '''    if seller_top5_result and _seller_result_status not in {"INVENTORY_PARTIAL", "PROFILE_INCOMPLETE"}:\n        seller_name = seller_top5_result.get("seller") or str(seller_top5_alias or "").strip()\n        inv_count = int(seller_top5_result.get("inventory_count") or 0)\n        st.markdown(f"### 🏆 Top 5 hos {seller_name}")\n'''
new_gate = '''    if seller_top5_result and _seller_result_status != "PROFILE_INCOMPLETE":\n        seller_name = seller_top5_result.get("seller") or str(seller_top5_alias or "").strip()\n        inv_count = int(seller_top5_result.get("inventory_count") or 0)\n        if _seller_result_status == "INVENTORY_PARTIAL":\n            st.markdown(f"### 🏆 Preliminär Top 5 hos {seller_name}")\n            st.caption("Listan uppdateras när fler 10-sidorsblock läses in. Kort kan flytta upp, ner eller försvinna när bättre fynd hittas.")\n        else:\n            st.markdown(f"### 🏆 Slutlig Top 5 hos {seller_name}")\n'''
if old_gate in text:
    text = text.replace(old_gate, new_gate, 1)
elif 'Preliminär Top 5 hos' not in text:
    raise SystemExit('app Top 5 render gate not found')

if text != original:
    app.write_text(text, encoding='utf-8')

print('patched dynamic provisional Seller Top 5 and 30-candidate final analysis')
