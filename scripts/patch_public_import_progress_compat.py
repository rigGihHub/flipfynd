from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")
old = '''                elif str(seller_top5_profile_url or "").strip():
                    try:
                        imported = fetch_public_seller_inventory_batch(
                            str(seller_top5_profile_url).strip(),
                            start_page=import_next_page,
                            max_pages=12,
                            progress_callback=_seller_import_progress,
                        )
                    except TypeError as exc:
                        if "progress_callback" not in str(exc):
                            raise
                        import_status_box.write("Deployen synkas fortfarande – fortsätter utan live-progress i detta block.")
                        imported = fetch_public_seller_inventory_batch(
                            str(seller_top5_profile_url).strip(),
                            start_page=import_next_page,
                            max_pages=12,
                        )
'''
new = '''                elif str(seller_top5_profile_url or "").strip():
                    try:
                        imported = fetch_public_seller_inventory_batch(
                            str(seller_top5_profile_url).strip(),
                            start_page=import_next_page,
                            max_pages=12,
                            progress_callback=_seller_import_progress,
                            fallback_alias=import_alias,
                        )
                    except TypeError as exc:
                        msg = str(exc)
                        if "fallback_alias" in msg:
                            import_status_box.write("Deployen synkas fortfarande – använder kompatibilitetsläge för säljaralias.")
                            try:
                                imported = fetch_public_seller_inventory_batch(
                                    str(seller_top5_profile_url).strip(),
                                    start_page=import_next_page,
                                    max_pages=12,
                                    progress_callback=_seller_import_progress,
                                )
                            except TypeError as inner_exc:
                                if "progress_callback" not in str(inner_exc):
                                    raise
                                import_status_box.write("Fortsätter utan live-progress i detta block.")
                                imported = fetch_public_seller_inventory_batch(
                                    str(seller_top5_profile_url).strip(),
                                    start_page=import_next_page,
                                    max_pages=12,
                                )
                        elif "progress_callback" in msg:
                            import_status_box.write("Deployen synkas fortfarande – fortsätter utan live-progress i detta block.")
                            try:
                                imported = fetch_public_seller_inventory_batch(
                                    str(seller_top5_profile_url).strip(),
                                    start_page=import_next_page,
                                    max_pages=12,
                                    fallback_alias=import_alias,
                                )
                            except TypeError as inner_exc:
                                if "fallback_alias" not in str(inner_exc):
                                    raise
                                imported = fetch_public_seller_inventory_batch(
                                    str(seller_top5_profile_url).strip(),
                                    start_page=import_next_page,
                                    max_pages=12,
                                )
                        else:
                            raise
'''
if old in text:
    text = text.replace(old, new, 1)
elif 'fallback_alias=import_alias' not in text:
    raise SystemExit('public seller import block not found')
path.write_text(text, encoding='utf-8')
print('Public seller ID-only profile compatibility patch applied')
