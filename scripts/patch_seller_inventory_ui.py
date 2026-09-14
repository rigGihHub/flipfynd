from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

import_anchor = "from src.tradera_seller_inventory import discover_active_seller_inventory\n"
import_new = (
    "from src.tradera_seller_inventory import discover_active_seller_inventory\n"
    "from src.public_seller_inventory import fetch_public_seller_inventory_batch\n"
)
if "from src.public_seller_inventory import fetch_public_seller_inventory_batch" not in text:
    if import_anchor not in text:
        raise SystemExit("public seller import anchor missing")
    text = text.replace(import_anchor, import_new, 1)

alias_anchor = '    seller_top5_alias = st.text_input("Säljarnamn", key="seller_top5_alias", placeholder="t.ex. Etanol71")\n'
alias_new = alias_anchor + '''    seller_top5_profile_url = st.text_input(
        "Tradera-profillänk (valfri)",
        key="seller_top5_profile_url",
        placeholder="https://www.tradera.com/profile/items/...",
        help="Behövs som fallback när Tradera API saknas. Öppna säljarens profilsida på Tradera och klistra in länken.",
    )
'''
if "seller_top5_profile_url = st.text_input" not in text:
    if alias_anchor not in text:
        raise SystemExit("seller alias input anchor missing")
    text = text.replace(alias_anchor, alias_new, 1)

resolve_old = '''                    credentials=creds,
                    quick_limit=60,
                    full_limit=10,
'''
resolve_new = '''                    credentials=creds,
                    profile_url=seller_top5_profile_url,
                    quick_limit=60,
                    full_limit=10,
'''
if "profile_url=seller_top5_profile_url" not in text:
    if resolve_old not in text:
        raise SystemExit("resolve_seller_top5 call anchor missing")
    text = text.replace(resolve_old, resolve_new, 1)

result_anchor = '    seller_top5_result = st.session_state.get("seller_top5_result")\n'
import_block = '''
    import_alias = str(seller_top5_alias or "").strip()
    import_cursor_key = f"seller_inventory_next_page::{import_alias.casefold()}" if import_alias else "seller_inventory_next_page"
    import_next_page = int(st.session_state.get(import_cursor_key, 1) or 1)
    import_label = "📥 Läs in säljarens annonser för analys" if import_next_page <= 1 else f"📥 Läs in nästa annonser (från sida {import_next_page})"
    if st.button(import_label, key="seller_inventory_import", use_container_width=True):
        if not import_alias:
            st.warning("Ange ett säljarnamn först.")
        else:
            creds = _resolve_tradera_api_credentials()
            with st.spinner(f"Läser in annonser från {import_alias}…"):
                imported = None
                if creds:
                    imported = discover_active_seller_inventory(
                        seller_alias=import_alias,
                        app_id=creds[0],
                        app_key=creds[1],
                        category_id=0,
                    )
                    if imported.get("ok"):
                        items = imported.get("items") or []
                        total_saved = save_expansion_items(SEARCH_EXPANSION_DATA_PATH, items)
                        get_data.clear()
                        st.session_state["result_cache"] = {}
                        st.session_state["seller_inventory_import_status"] = {
                            "ok": True,
                            "source": "TRADERA_API",
                            "batch_count": len(items),
                            "total_saved": total_saved,
                            "complete": True,
                            "seller": import_alias,
                        }
                elif str(seller_top5_profile_url or "").strip():
                    imported = fetch_public_seller_inventory_batch(
                        str(seller_top5_profile_url).strip(),
                        start_page=import_next_page,
                        max_pages=12,
                    )
                    if imported.get("ok"):
                        items = imported.get("items") or []
                        total_saved = save_expansion_items(SEARCH_EXPANSION_DATA_PATH, items)
                        get_data.clear()
                        st.session_state["result_cache"] = {}
                        exhausted = bool(imported.get("exhausted"))
                        st.session_state[import_cursor_key] = 1 if exhausted else int(imported.get("next_page") or (import_next_page + 12))
                        st.session_state["seller_inventory_import_status"] = {
                            "ok": True,
                            "source": "TRADERA_PUBLIC_PROFILE",
                            "batch_count": len(items),
                            "pages_read": int(imported.get("pages_read") or 0),
                            "total_saved": total_saved,
                            "complete": exhausted,
                            "next_page": None if exhausted else st.session_state[import_cursor_key],
                            "seller": import_alias,
                        }
                else:
                    st.session_state["seller_inventory_import_status"] = {
                        "ok": False,
                        "status": "PROFILE_URL_REQUIRED",
                        "seller": import_alias,
                    }

                if imported is not None and not imported.get("ok"):
                    st.session_state["seller_inventory_import_status"] = {
                        "ok": False,
                        "status": imported.get("status") or "IMPORT_FAILED",
                        "seller": import_alias,
                    }

    seller_inventory_status = st.session_state.get("seller_inventory_import_status")
    if seller_inventory_status and seller_inventory_status.get("seller") == str(seller_top5_alias or "").strip():
        if seller_inventory_status.get("ok"):
            batch_count = int(seller_inventory_status.get("batch_count") or 0)
            total_saved = int(seller_inventory_status.get("total_saved") or 0)
            if seller_inventory_status.get("source") == "TRADERA_API":
                st.success(f"{batch_count} annonser lästes in. {total_saved} säljar-/sökannonser finns nu i analysunderlaget.")
            elif seller_inventory_status.get("complete"):
                st.success(f"Hela den publika säljarprofilen är genomläst. {total_saved} annonser finns nu i analysunderlaget.")
            else:
                pages_read = int(seller_inventory_status.get("pages_read") or 0)
                next_page = seller_inventory_status.get("next_page")
                st.success(f"{batch_count} annonser från {pages_read} profilsidor lästes in. Fortsätt från sida {next_page} för nästa block.")
        elif seller_inventory_status.get("status") == "PROFILE_URL_REQUIRED":
            st.warning("Tradera API är inte konfigurerat. Klistra in säljarens publika Tradera-profillänk ovan för att läsa in lagret.")
        else:
            st.error(f"Kunde inte läsa in säljarens annonser ({seller_inventory_status.get('status')}).")

'''
if "seller_inventory_import_status" not in text:
    if result_anchor not in text:
        raise SystemExit("seller result anchor missing")
    text = text.replace(result_anchor, import_block + result_anchor, 1)

source_old = '''        if inventory_source == "TRADERA_API":
            st.caption("Källa: live-inventarie via Tradera API.")
        elif inventory_source == "LOCAL_MARKET":
'''
source_new = '''        if inventory_source == "TRADERA_API":
            st.caption("Källa: live-inventarie via Tradera API.")
        elif inventory_source == "TRADERA_PUBLIC_PROFILE":
            pages_read = int(seller_top5_result.get("public_pages_read") or 0)
            st.caption(f"Källa: säljarens publika Tradera-profil · {pages_read} profilsidor lästa.")
        elif inventory_source == "LOCAL_MARKET":
'''
if "inventory_source == \"TRADERA_PUBLIC_PROFILE\"" not in text:
    if source_old not in text:
        raise SystemExit("inventory source UI anchor missing")
    text = text.replace(source_old, source_new, 1)

path.write_text(text, encoding="utf-8")
print("seller inventory UI patch applied")
