from pathlib import Path

# Compatibility patch. Controller v3 already owns five-page batches and
# per-page checkpoints. Keep only the app-side form persistence patch when v3
# is present, so CI never rewrites the controller back toward an older shape.

controller = Path('src/seller_top5_controller.py')
text = controller.read_text(encoding='utf-8')
controller_v3 = '_CHECKPOINT_SCHEMA = "v3"' in text and '_partial_result_from_saved' in text

if not controller_v3:
    original = text
    text = text.replace('from typing import Callable, Iterable\n', 'from typing import Callable, Iterable\n\nfrom src.seller_checkpoint_store import clear_checkpoint, load_checkpoint, save_checkpoint\n', 1)
    text = text.replace('PUBLIC_BATCH_PAGES = 10', 'PUBLIC_BATCH_PAGES = 5')

    old_load = '''        checkpoint = None\n        if session is not None:\n            checkpoint = session.get(key)\n        if not isinstance(checkpoint, dict):\n            checkpoint = {"next_page": 1, "pages_read": 0, "items": {}}\n'''
    new_load = '''        checkpoint = load_checkpoint(key, session=session)\n        if not isinstance(checkpoint, dict):\n            checkpoint = {"next_page": 1, "pages_read": 0, "items": {}}\n'''
    text = text.replace(old_load, new_load, 1)

    old_fetch = '''        try:\n            public = _fetch_public(\n                public_fetcher,\n                profile_text,\n                start_page=start_page,\n                public_pages=batch_pages,\n                progress_callback=combined_progress,\n                seller_alias=alias,\n            )\n        except Exception as exc:\n            public = {"ok": False, "status": "FETCH_EXCEPTION", "error": str(exc), "items": []}\n'''
    new_fetch = '''        public = None\n        current_page = start_page\n        pages_this_run = 0\n        exhausted = False\n        for _ in range(batch_pages):\n            try:\n                page_result = _fetch_public(\n                    public_fetcher, profile_text, start_page=current_page, public_pages=1,\n                    progress_callback=combined_progress, seller_alias=alias,\n                )\n            except Exception as exc:\n                page_result = {"ok": False, "status": "FETCH_EXCEPTION", "error": str(exc), "items": []}\n            if not page_result.get("ok"):\n                public = page_result\n                break\n            for item in page_result.get("items") or []:\n                if isinstance(item, dict):\n                    item_id = _item_key(item)\n                    if item_id:\n                        stored_items[item_id] = dict(item)\n            pages_this_run += int(page_result.get("pages_read") or 0)\n            current_page = int(page_result.get("next_page") or (current_page + 1))\n            exhausted = bool(page_result.get("exhausted"))\n            save_checkpoint(key, {"next_page": current_page, "pages_read": int(checkpoint.get("pages_read") or 0) + pages_this_run, "items": stored_items}, session=session)\n            if exhausted:\n                break\n        if public is None or public.get("ok"):\n            public = {"ok": True, "status": "OK", "items": list(stored_items.values()), "pages_read": pages_this_run, "next_page": current_page, "exhausted": exhausted}\n'''
    if old_fetch in text:
        text = text.replace(old_fetch, new_fetch, 1)
    elif 'pages_this_run' not in text:
        raise SystemExit('public batch fetch block not found')

    if text != original:
        controller.write_text(text, encoding='utf-8')
else:
    print('controller v3 already contains resume resilience')

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

print('Seller Top 5 resume compatibility patch complete')
