from pathlib import Path

controller = Path('src/seller_top5_controller.py')
text = controller.read_text(encoding='utf-8')
original = text
controller_v3 = '_CHECKPOINT_SCHEMA = "v3"' in text and '_partial_result_from_saved' in text

if not controller_v3:
    old = '''        public_failure = public\n\n    seller_rows = local_inventory_for_seller(alias, local_rows)\n'''
    new = '''        public_failure = public\n        saved_checkpoint = load_checkpoint(key, session=session) or checkpoint\n        saved_items = dict((saved_checkpoint or {}).get("items") or {})\n        saved_pages = int((saved_checkpoint or {}).get("pages_read") or 0)\n        saved_next_page = max(1, int((saved_checkpoint or {}).get("next_page") or start_page))\n        return {\n            "status": "INVENTORY_PARTIAL",\n            "seller": alias,\n            "rows": [],\n            "inventory_count": len(saved_items),\n            "inventory_source": "TRADERA_PUBLIC_PROFILE",\n            "public_status": (public_failure or {}).get("status") or "FETCH_FAILED",\n            "public_error": (public_failure or {}).get("error"),\n            "public_pages_read": saved_pages,\n            "public_next_page": saved_next_page,\n            "public_batch_pages": 0,\n            "public_inventory_complete": False,\n            "provisional_top5": False,\n            "resume_required": True,\n            "fallback_reason": "PUBLIC_PROFILE_INTERRUPTED",\n            "api_status": (api_failure or {}).get("status") if api_failure else ("NOT_CONFIGURED" if not creds else "OK"),\n        }\n\n    seller_rows = local_inventory_for_seller(alias, local_rows)\n'''
    if old in text:
        text = text.replace(old, new, 1)
    elif '"resume_required": True' not in text:
        raise SystemExit('profile failure fallback block not found')
    if text != original:
        controller.write_text(text, encoding='utf-8')
else:
    print('controller v3 already contains interrupted-profile resume guard')

app = Path('app.py')
text = app.read_text(encoding='utf-8')
original = text

text = text.replace(
    'seller_status.update(label=f"📥 5-sidorsblock klart för {alias}", state="complete", expanded=False)',
    'seller_status.update(label=f"📥 Block sparat för {alias} · fortsätt nästa 5 sidor", state="complete", expanded=False)',
)

old_partial = '''    if seller_top5_result and _seller_result_status == "INVENTORY_PARTIAL":\n        _saved = int(seller_top5_result.get("inventory_count") or 0)\n        _pages = int(seller_top5_result.get("public_pages_read") or 0)\n        _next = int(seller_top5_result.get("public_next_page") or 1)\n        st.info(f"📥 Inventering pågår: {_pages} profilsidor lästa och {_saved} unika annonser sparade. Nästa block börjar på sida {_next}. Preliminär Top 5 uppdateras löpande; tryck på ‘Fortsätt läsa nästa 5 sidor’.")\n'''
new_partial = '''    if seller_top5_result and _seller_result_status == "INVENTORY_PARTIAL":\n        _saved = int(seller_top5_result.get("inventory_count") or 0)\n        _pages = int(seller_top5_result.get("public_pages_read") or 0)\n        _next = int(seller_top5_result.get("public_next_page") or 1)\n        if seller_top5_result.get("resume_required"):\n            st.warning(f"📥 Inläsningen avbröts, men checkpointen är sparad. {_pages} profilsidor och {_saved} annonser är bevarade. Tryck på ‘Fortsätt läsa nästa 5 sidor’ för att fortsätta från sida {_next}.")\n        else:\n            st.info(f"📥 Inventering pågår: {_pages} profilsidor lästa och {_saved} unika annonser sparade. Nästa block börjar på sida {_next}. Preliminär Top 5 uppdateras löpande; tryck på ‘Fortsätt läsa nästa 5 sidor’.")\n'''
if old_partial in text:
    text = text.replace(old_partial, new_partial, 1)
elif 'checkpointen är sparad' not in text and 'Inventering pågår:' not in text:
    raise SystemExit('partial inventory status block not found')

old_gate = '    if seller_top5_result and _seller_result_status != "PROFILE_INCOMPLETE":\n'
new_gate = '    if seller_top5_result and _seller_result_status != "PROFILE_INCOMPLETE" and (seller_top5_result.get("rows") or []):\n'
if old_gate in text:
    text = text.replace(old_gate, new_gate, 1)

if text != original:
    app.write_text(text, encoding='utf-8')

print('Seller Top 5 interrupted-profile compatibility patch complete')
