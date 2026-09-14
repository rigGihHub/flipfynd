from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')
original = text

text = text.replace(
    '_seller_continue_inventory = str(_seller_previous_result.get("status") or "") == "INVENTORY_PARTIAL"',
    '_seller_continue_inventory = str(_seller_previous_result.get("status") or "") in {"INVENTORY_PARTIAL", "PROFILE_INCOMPLETE"}',
)
text = text.replace(
    '_seller_button_label = "📥 Fortsätt läsa nästa 5 sidor" if _seller_continue_inventory else "🔎 Läs in & ranka säljarens 5 bästa"',
    '_seller_button_label = "📥 Fortsätt läsa nästa 5 sidor" if _seller_continue_inventory else "🔎 Läs in & ranka säljarens 5 bästa"',
)

# Avoid contradictory completion wording when the profile is not complete.
text = text.replace(
    'seller_progress_bar.progress(0, text="Profilinläsningen behöver fortsätta")',
    'seller_progress_bar.progress(0, text="Profilinläsningen behöver fortsätta · tryck på Fortsätt läsa nästa 5 sidor")',
)

if text == original:
    raise SystemExit('No Seller Top 5 incomplete-profile UI patch applied')

p.write_text(text, encoding='utf-8')
print('patched PROFILE_INCOMPLETE to expose continue button')
