from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")
old = '''                        get_data.clear()\n                        st.session_state["result_cache"] = {}\n                        exhausted = bool(imported.get("exhausted"))\n'''
new = '''                        get_data.clear()\n                        st.session_state["result_cache"] = {}\n                        triage_market = get_data(get_data_version())\n                        triage_sport = "hockey" if seller_top5_sport_label == "Hockey" else "football"\n                        st.session_state["seller_inventory_triage_result"] = build_seller_inventory_triage(\n                            import_alias,\n                            triage_market,\n                            analyze_fn=analyze_item,\n                            sport=triage_sport,\n                            max_fast_analyses=120,\n                            top_n=20,\n                        )\n                        exhausted = bool(imported.get("exhausted"))\n'''
if old in text:
    text = text.replace(old, new, 1)
elif 'exhausted = bool(imported.get("exhausted"))' in text and text.count('seller_inventory_triage_result') >= 3:
    pass
else:
    raise SystemExit("public profile auto-triage anchor missing")
path.write_text(text, encoding="utf-8")
print("Public profile auto-triage patch applied")
