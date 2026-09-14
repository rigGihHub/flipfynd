from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")
old = '''                elif str(seller_top5_profile_url or "").strip():
                    imported = fetch_public_seller_inventory_batch(
                        str(seller_top5_profile_url).strip(),
                        start_page=import_next_page,
                        max_pages=12,
                        progress_callback=_seller_import_progress,
                    )
'''
new = '''                elif str(seller_top5_profile_url or "").strip():
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
if old in text:
    text = text.replace(old, new, 1)
elif 'fortsätter utan live-progress i detta block' not in text:
    raise SystemExit('public seller import block not found')
path.write_text(text, encoding='utf-8')
print('Public seller import progress compatibility patch applied')
