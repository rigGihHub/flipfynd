from pathlib import Path

# Make Seller Top 5 resilient to dropped Streamlit sessions:
# - five pages per visible batch
# - checkpoint every fetched page
# - mirror checkpoints to local disk through seller_checkpoint_store
# - persist seller/profile in URL query params so form fields survive reconnects

controller = Path('src/seller_top5_controller.py')
text = controller.read_text(encoding='utf-8')
original = text

text = text.replace('from typing import Callable, Iterable\n', 'from typing import Callable, Iterable\n\nfrom src.seller_checkpoint_store import clear_checkpoint, load_checkpoint, save_checkpoint\n', 1)
text = text.replace('PUBLIC_BATCH_PAGES = 10', 'PUBLIC_BATCH_PAGES = 5')

old_load = '''        checkpoint = None\n        if session is not None:\n            checkpoint = session.get(key)\n        if not isinstance(checkpoint, dict):\n            checkpoint = {"next_page": 1, "pages_read": 0, "items": {}}\n'''
new_load = '''        checkpoint = load_checkpoint(key, session=session)\n        if not isinstance(checkpoint, dict):\n            checkpoint = {"next_page": 1, "pages_read": 0, "items": {}}\n'''
text = text.replace(old_load, new_load, 1)

old_fetch = '''        try:\n            public = _fetch_public(\n                public_fetcher,\n                profile_text,\n                start_page=start_page,\n                public_pages=batch_pages,\n                progress_callback=combined_progress,\n                seller_alias=alias,\n            )\n        except Exception as exc:\n            public = {"ok": False, "status": "FETCH_EXCEPTION", "error": str(exc), "items": []}\n'''
new_fetch = '''        # Fetch one page at a time and persist a checkpoint immediately after\n        # every successful page. A dropped Streamlit session therefore loses at\n        # most the in-flight page, not the entire block.\n        public = None\n        current_page = start_page\n        pages_this_run = 0\n        exhausted = False\n        for _ in range(batch_pages):\n            try:\n                page_result = _fetch_public(\n                    public_fetcher,\n                    profile_text,\n                    start_page=current_page,\n                    public_pages=1,\n                    progress_callback=combined_progress,\n                    seller_alias=alias,\n                )\n            except Exception as exc:\n                page_result = {"ok": False, "status": "FETCH_EXCEPTION", "error": str(exc), "items": []}\n            if not page_result.get("ok"):\n                public = page_result\n                break\n            for item in page_result.get("items") or []:\n                if isinstance(item, dict):\n                    item_id = _item_key(item)\n                    if item_id:\n                        stored_items[item_id] = dict(item)\n            pages_this_run += int(page_result.get("pages_read") or 0)\n            current_page = int(page_result.get("next_page") or (current_page + 1))\n            exhausted = bool(page_result.get("exhausted"))\n            save_checkpoint(\n                key,\n                {\n                    "next_page": current_page,\n                    "pages_read": int(checkpoint.get("pages_read") or 0) + pages_this_run,\n                    "items": stored_items,\n                },\n                session=session,\n            )\n            if exhausted:\n                break\n        if public is None or public.get("ok"):\n            public = {\n                "ok": True,\n                "status": "OK",\n                "items": list(stored_items.values()),\n                "pages_read": pages_this_run,\n                "next_page": current_page,\n                "exhausted": exhausted,\n            }\n'''
if old_fetch in text:
    text = text.replace(old_fetch, new_fetch, 1)
elif 'Fetch one page at a time and persist a checkpoint immediately' not in text:
    raise SystemExit('public batch fetch block not found')

old_save = '''                if session is not None:\n                    session[key] = {\n                        "next_page": next_page,\n                        "pages_read": total_pages_read,\n                        "items": stored_items,\n                    }\n'''
new_save = '''                save_checkpoint(\n                    key,\n                    {"next_page": next_page, "pages_read": total_pages_read, "items": stored_items},\n                    session=session,\n                )\n'''
text = text.replace(old_save, new_save, 1)

old_clear = '''            if session is not None:\n                try:\n                    del session[key]\n                except Exception:\n                    pass\n'''
new_clear = '''            clear_checkpoint(key, session=session)\n'''
text = text.replace(old_clear, new_clear, 1)

if text != original:
    controller.write_text(text, encoding='utf-8')

app = Path('app.py')
text = app.read_text(encoding='utf-8')
original = text

marker = '# SELLER_TOP5_UI_V1\nwith st.sidebar.expander("🏪 Säljare – Top 5 fynd", expanded=False):\n'
insert = '''# SELLER_TOP5_UI_V1\n# Restore Seller Top 5 form values after a Streamlit websocket/session reset.\ntry:\n    _seller_qp_alias = str(st.query_params.get("seller", "") or "").strip()\n    _seller_qp_profile = str(st.query_params.get("seller_profile", "") or "").strip()\nexcept Exception:\n    _seller_qp_alias = ""\n    _seller_qp_profile = ""\nif "seller_top5_alias" not in st.session_state and _seller_qp_alias:\n    st.session_state["seller_top5_alias"] = _seller_qp_alias\nif "seller_top5_profile_url" not in st.session_state and _seller_qp_profile:\n    st.session_state["seller_top5_profile_url"] = _seller_qp_profile\nwith st.sidebar.expander("🏪 Säljare – Top 5 fynd", expanded=False):\n'''
if marker in text:
    text = text.replace(marker, insert, 1)
elif '_seller_qp_alias' not in text:
    raise SystemExit('Seller Top 5 UI marker not found')

profile_block = '''    seller_top5_profile_url = st.text_input(\n        "Tradera-profillänk (valfri)",\n        key="seller_top5_profile_url",\n        placeholder="https://www.tradera.com/profile/items/...",\n        help="Behövs som fallback när Tradera API saknas. Öppna säljarens profilsida på Tradera och klistra in länken.",\n    )\n'''
profile_replacement = profile_block + '''    try:\n        if seller_top5_alias and str(st.query_params.get("seller", "") or "") != str(seller_top5_alias):\n            st.query_params["seller"] = str(seller_top5_alias)\n        if seller_top5_profile_url and str(st.query_params.get("seller_profile", "") or "") != str(seller_top5_profile_url):\n            st.query_params["seller_profile"] = str(seller_top5_profile_url)\n    except Exception:\n        pass\n'''
if profile_block in text:
    text = text.replace(profile_block, profile_replacement, 1)
elif 'st.query_params["seller_profile"]' not in text:
    raise SystemExit('Seller Top 5 profile input block not found')

text = text.replace('Fortsätt läsa nästa 10 sidor', 'Fortsätt läsa nästa 5 sidor')
text = text.replace('10-sidorsblock', '5-sidorsblock')
text = text.replace('fler 10-sidorsblock', 'fler 5-sidorsblock')

if text != original:
    app.write_text(text, encoding='utf-8')

print('patched Seller Top 5 resume resilience: 5-page batches, per-page checkpoints, URL form persistence')
