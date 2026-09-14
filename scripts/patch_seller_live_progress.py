from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

old_top5 = '''            seller_status = st.status(f"🔎 Söker igenom {alias}…", expanded=True)\n            seller_status.write("Startar säljarinventering och prioritering av kandidater.")\n            try:\n                try:\n                    top5 = resolve_seller_top5(\n                        alias,\n                        local_market,\n                        analyze_fn=analyze_item,\n                        sport=sport_key,\n                        credentials=creds,\n                        profile_url=seller_top5_profile_url,\n                        quick_limit=60,\n                        full_limit=10,\n                    )\n'''
new_top5 = '''            seller_status = st.status(f"🔎 Söker igenom {alias}…", expanded=True)\n            seller_progress_line = seller_status.empty()\n            seller_status.write("Startar säljarinventering och prioritering av kandidater.")\n\n            def _seller_search_progress(info):\n                phase = str((info or {}).get("phase") or "")\n                page = int((info or {}).get("page") or 0)\n                found = int((info or {}).get("found_count") or 0)\n                pages_read = int((info or {}).get("pages_read") or 0)\n                max_pages = int((info or {}).get("max_pages") or 0)\n                if phase == "fetching":\n                    seller_progress_line.info(f"📄 Läser profilsida {page} · {found} unika annonser hittade hittills")\n                elif phase == "page_complete":\n                    seller_progress_line.success(f"Sida {page} klar · {found} unika annonser hittade · {pages_read}/{max_pages} sidor i detta block")\n                elif phase == "exhausted":\n                    seller_progress_line.success(f"Profilens slut nått vid sida {page} · {found} unika annonser hittade")\n                elif phase == "complete":\n                    seller_progress_line.info(f"Inventering klar · {found} annonser · går vidare till analys")\n\n            try:\n                try:\n                    top5 = resolve_seller_top5(\n                        alias,\n                        local_market,\n                        analyze_fn=analyze_item,\n                        sport=sport_key,\n                        credentials=creds,\n                        profile_url=seller_top5_profile_url,\n                        progress_callback=_seller_search_progress,\n                        quick_limit=60,\n                        full_limit=10,\n                    )\n'''
if old_top5 not in text:
    if "def _seller_search_progress(info):" not in text:
        raise SystemExit("Top5 progress anchor missing")
else:
    text = text.replace(old_top5, new_top5, 1)

old_compat = '''                    if "profile_url" not in str(exc):\n                        raise\n                    seller_status.write("Deployen synkas fortfarande – använder kompatibilitetsläge.")\n'''
new_compat = '''                    if "profile_url" not in str(exc) and "progress_callback" not in str(exc):\n                        raise\n                    seller_status.write("Deployen synkas fortfarande – använder kompatibilitetsläge.")\n'''
if old_compat in text:
    text = text.replace(old_compat, new_compat, 1)

old_import = '''            creds = _resolve_tradera_api_credentials()\n            with st.spinner(f"Läser in annonser från {import_alias}…"):\n                imported = None\n'''
new_import = '''            creds = _resolve_tradera_api_credentials()\n            import_status_box = st.status(f"📥 Läser in annonser från {import_alias}…", expanded=True)\n            import_progress_line = import_status_box.empty()\n\n            def _seller_import_progress(info):\n                phase = str((info or {}).get("phase") or "")\n                page = int((info or {}).get("page") or 0)\n                found = int((info or {}).get("found_count") or 0)\n                pages_read = int((info or {}).get("pages_read") or 0)\n                max_pages = int((info or {}).get("max_pages") or 0)\n                if phase == "fetching":\n                    import_progress_line.info(f"📄 Läser profilsida {page} · {found} unika annonser hittade hittills")\n                elif phase == "page_complete":\n                    import_progress_line.success(f"Sida {page} klar · {found} unika annonser hittade · {pages_read}/{max_pages} sidor i detta block")\n                elif phase == "exhausted":\n                    import_progress_line.success(f"Profilens slut nått · {found} annonser hittade")\n                elif phase == "complete":\n                    import_progress_line.info(f"Importblocket klart · {found} annonser · startar triage")\n\n            with import_status_box:\n                imported = None\n'''
if old_import not in text:
    if "def _seller_import_progress(info):" not in text:
        raise SystemExit("Import progress anchor missing")
else:
    text = text.replace(old_import, new_import, 1)

old_fetch = '''                    imported = fetch_public_seller_inventory_batch(\n                        str(seller_top5_profile_url).strip(),\n                        start_page=import_next_page,\n                        max_pages=12,\n                    )\n'''
new_fetch = '''                    imported = fetch_public_seller_inventory_batch(\n                        str(seller_top5_profile_url).strip(),\n                        start_page=import_next_page,\n                        max_pages=12,\n                        progress_callback=_seller_import_progress,\n                    )\n'''
if old_fetch in text:
    text = text.replace(old_fetch, new_fetch, 1)
elif "progress_callback=_seller_import_progress" not in text:
    raise SystemExit("Public import call anchor missing")

# Final status after import attempt. Put it immediately before the saved status rendering.
anchor = '''    seller_inventory_status = st.session_state.get("seller_inventory_import_status")\n'''
status_code = '''            if imported is not None and imported.get("ok"):\n                import_status_box.update(label=f"✅ Importblock klart för {import_alias}", state="complete", expanded=False)\n            elif imported is not None:\n                import_status_box.update(label=f"❌ Importen av {import_alias} avbröts", state="error", expanded=True)\n\n    seller_inventory_status = st.session_state.get("seller_inventory_import_status")\n'''
if "Importblock klart för {import_alias}" not in text:
    if anchor not in text:
        raise SystemExit("Import status render anchor missing")
    text = text.replace(anchor, status_code, 1)

path.write_text(text, encoding="utf-8")
print("Seller live-progress patch applied")
