# FlipFynd v0.12.15 – Exact Supply History

- Ny `src/exact_supply_history.py`.
- Bekräftat exact-supply kan nu sparas som tidsstämplade snapshots per exakt identitetsnyckel.
- Snapshot lagrar endast observerade fakta: bekräftade exakta, möjliga och fel kort/konflikt.
- Historiken är strikt identitetsseparerad per spelare + set + säsong + kortnummer + relevanta variant/graderingsfält.
- Minst två snapshots krävs innan någon riktning visas.
- Riktningar: `MINSKAT_OBSERVERAT_UTBUD`, `ÖKAT_OBSERVERAT_UTBUD`, `OFÖRÄNDRAT_OBSERVERAT_UTBUD`, annars `EJ_BEDÖMBAR`.
- Riktningen gäller bara sparade FlipFynd-observationer och är inte ett påstående om hela marknaden.
- Ingen scarcity-score skapas.
- Historiken påverkar aldrig KÖP, marknadsvärde eller maxpris.
- Ny knapp i Exact Card Supply: **Spara exact-supply observation**.
