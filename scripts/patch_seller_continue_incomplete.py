from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')
original = text

old_continue = '_seller_continue_inventory = str(_seller_previous_result.get("status") or "") == "INVENTORY_PARTIAL"'
new_continue = '_seller_continue_inventory = str(_seller_previous_result.get("status") or "") in {"INVENTORY_PARTIAL", "PROFILE_INCOMPLETE"}'
if old_continue in text:
    text = text.replace(old_continue, new_continue, 1)

old_progress = 'seller_progress_bar.progress(0, text="Profilinläsningen behöver fortsätta")'
new_progress = 'seller_progress_bar.progress(0, text="Profilinläsningen behöver fortsätta · tryck på Fortsätt läsa nästa 5 sidor")'
if old_progress in text:
    text = text.replace(old_progress, new_progress, 1)

# This CI patch is intentionally idempotent. If the desired behavior is already
# present in app.py, a repeated workflow run must succeed instead of failing.
already_continue = new_continue in text
already_progress = (
    new_progress in text
    or 'Fortsätt läsa nästa 5 sidor' in text
)

if text != original:
    p.write_text(text, encoding='utf-8')
    print('patched PROFILE_INCOMPLETE to expose continue button')
elif already_continue and already_progress:
    print('Seller Top 5 incomplete-profile continue patch already applied')
else:
    raise SystemExit('Seller Top 5 incomplete-profile UI target not found')
