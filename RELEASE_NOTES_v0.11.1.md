# FlipFynd v0.11.1 – Retro Result Cards

## Nytt
- Resultatkorten har fått en tydligare retro/samlarkorts-känsla.
- Varje kandidat visar direkt rank, beslut och Fyndpoäng som tydliga badges.
- Fyra viktigaste beslutsvärdena ligger nu högst upp: aktuellt/köppris, realistiskt värde, möjlig nettovinst och säljchans.
- Mobil layout växlar automatiskt från fyra till två kolumner.
- Samma retro-palett från v0.11.0 används konsekvent: cream, orange, teal och guld.
- Analyslogik och värdering är oförändrade i denna release.

## QA
- `python -m compileall -q .` passerar.
- `pytest -q`: 263/263 tester passerar.
