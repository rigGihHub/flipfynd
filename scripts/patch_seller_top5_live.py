from pathlib import Path

# One-time deterministic patch for wiring Seller Top 5 into the live app.
path = Path("app.py")
text = path.read_text(encoding="utf-8")

import_old = "from src.seller_top5 import build_seller_top5\n"
import_new = (
    "from src.seller_top5 import build_seller_top5\n"
    "from src.seller_top5_controller import resolve_seller_top5\n"
)
if "from src.seller_top5_controller import resolve_seller_top5" not in text:
    if import_old not in text:
        raise SystemExit("seller_top5 import anchor not found")
    text = text.replace(import_old, import_new, 1)

old = '''            creds = _resolve_tradera_api_credentials()
            if not creds:
                st.error("Tradera API är inte konfigurerat i miljön, så säljarens aktiva annonser kan inte hämtas automatiskt ännu.")
            else:
                with st.spinner(f"Hämtar och analyserar aktiva annonser från {alias}…"):
                    fetched = discover_active_seller_inventory(
                        seller_alias=alias,
                        app_id=creds[0],
                        app_key=creds[1],
                        category_id=0,
                    )
                    if not fetched.get("ok"):
                        st.error("Kunde inte hämta säljarens aktiva annonser från Tradera.")
                        if fetched.get("status"):
                            st.caption(f"Status: {fetched.get('status')}")
                    else:
                        items = fetched.get("items") or []
                        sport_key = "hockey" if seller_top5_sport_label == "Hockey" else "fotboll"
                        top5 = build_seller_top5(
                            alias,
                            items,
                            analyze_fn=analyze_item,
                            sport=sport_key,
                            quick_limit=60,
                            full_limit=10,
                        )
                        st.session_state["seller_top5_result"] = top5
'''
new = '''            creds = _resolve_tradera_api_credentials()
            sport_key = "hockey" if seller_top5_sport_label == "Hockey" else "football"
            local_market = get_data(get_data_version())
            with st.spinner(f"Hämtar och analyserar annonser från {alias}…"):
                top5 = resolve_seller_top5(
                    alias,
                    local_market,
                    analyze_fn=analyze_item,
                    sport=sport_key,
                    credentials=creds,
                    quick_limit=60,
                    full_limit=10,
                )
                st.session_state["seller_top5_result"] = top5
'''
if old in text:
    text = text.replace(old, new, 1)
elif "top5 = resolve_seller_top5(" not in text:
    raise SystemExit("Seller Top 5 UI anchor not found and integration not already present")

summary_old = '''        st.caption(
            f"{inv_count} aktiva annonser hittades · "
            f"{int(seller_top5_result.get('quick_analysed') or 0)} snabbanalyserade · "
            f"{int(seller_top5_result.get('full_analysed') or 0)} fullanalyserade"
        )
'''
summary_new = '''        st.caption(
            f"{inv_count} annonser hittades · "
            f"{int(seller_top5_result.get('quick_analysed') or 0)} snabbanalyserade · "
            f"{int(seller_top5_result.get('full_analysed') or 0)} fullanalyserade"
        )
        inventory_source = seller_top5_result.get("inventory_source")
        if inventory_source == "TRADERA_API":
            st.caption("Källa: live-inventarie via Tradera API.")
        elif inventory_source == "LOCAL_MARKET":
            reason = seller_top5_result.get("fallback_reason")
            if reason == "NO_API_CREDENTIALS":
                st.caption("Källa: redan inläst FlipFynd-data · Tradera API är inte konfigurerat.")
            elif reason == "API_FAILED":
                api_status = seller_top5_result.get("api_status") or "okänt fel"
                st.caption(f"Källa: redan inläst FlipFynd-data · API-fallback efter {api_status}.")
            else:
                st.caption("Källa: redan inläst FlipFynd-data.")
'''
if summary_old in text:
    text = text.replace(summary_old, summary_new, 1)
elif "inventory_source = seller_top5_result.get" not in text:
    raise SystemExit("Seller Top 5 summary anchor not found and source UI not already present")

path.write_text(text, encoding="utf-8")
print("Seller Top 5 live integration patch applied")
