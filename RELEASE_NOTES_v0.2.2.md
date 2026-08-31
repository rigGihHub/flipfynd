# FlipFynd v0.2.2 – Chromium fallback + versionsnummer

## Ändrat
- Visar alltid appversion direkt under FlipFynd-rubriken.
- Försöker först använda system-Chromium om det finns.
- Om Chromium saknas installerar appen automatiskt Playwrights Chromium-bundle och försöker starta igen.
- Tydligare felmeddelande om browserinstallationen ändå misslyckas.

## Verifierat här
- Python compileall körd utan syntaxfel.

## Ej verifierat här
- Själva Chromium-starten på Streamlit Community Cloud måste verifieras efter deploy.
