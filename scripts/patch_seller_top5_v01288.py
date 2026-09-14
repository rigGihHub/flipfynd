from pathlib import Path

# FlipFynd v0.12.88 — read exactly one public seller-profile page per click.

p = Path('src/seller_top5_controller.py')
text = p.read_text(encoding='utf-8')
text = text.replace('PUBLIC_BATCH_PAGES = 5', 'PUBLIC_BATCH_PAGES = 1')
text = text.replace('This keeps each 5-page request short enough for\n    Streamlit while still showing the best five candidates found so far.', 'This keeps each one-page request short enough for\n    Streamlit while still showing the best five candidates found so far.')
p.write_text(text, encoding='utf-8')

p = Path('app.py')
text = p.read_text(encoding='utf-8')
text = text.replace('APP_VERSION = "v0.12.87"', 'APP_VERSION = "v0.12.88"')
text = text.replace('APP_VERSION = "v0.12.86"', 'APP_VERSION = "v0.12.88"')
text = text.replace('Fortsätt läsa nästa 5 sidor', 'Läs nästa sida')
text = text.replace('Fortsätt läsa nästa 5 sidor', 'Läs nästa sida')
text = text.replace('fortsätt nästa 5 sidor', 'fortsätt till nästa sida')
p.write_text(text, encoding='utf-8')

print('patched FlipFynd v0.12.88: one seller-profile page per click')
