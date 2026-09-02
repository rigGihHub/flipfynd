# FlipFynd v0.10.2 – Player × Card Demand Engine

- Ny modul `src/player_card_demand.py`.
- Ny kunskapsfil `data/player_card_demand.json` med strukturella efterfrågearketyper utan prisfaktorer.
- Ny separat efterfrågescore 0–100 som kombinerar:
  - spelarefterfrågan,
  - kortstruktur,
  - observerad marknad/omsättning.
- Ny **evidenssäkerhet** som visar hur väl efterfrågeprofilen faktiskt stöds av sold comps, identitet och värderingsunderlag.
- Ny **analysprioritet** som kan hjälpa FlipFynd välja vilka annonser som ska få full analys först.
- Preselection-boost är hårt begränsad till max 12 poäng och påverkar inte slutligt marknadsvärde, vinst, ROI eller maxbud.
- Avsaknad av sold comps behandlas som osäkerhet, inte automatiskt låg efterfrågan.
- Okänd spelare, svag spelarefterfrågan och låg identitet får konservativa caps.
- Ny UI-sektion `🎯 Player × Card Demand Engine` med spelare, kortstruktur, marknad, evidenssäkerhet och nästa åtgärd.
- Cachemodell uppdaterad till `flip_v20_player_card_demand`.
- Versionen visas som v0.10.2.

## QA

- 226/226 enhetstester passerar.
- `python -m compileall -q .` passerar.
- Separat smoke-test: stark spelare + premiumstruktur + 4 sold comps gav efterfrågan 93/100, evidenssäkerhet 84/100 och analysprioritet 86/100 utan att bli säker för värdering (`safe_for_valuation=False`).
- Ingen liveverifiering av Streamlit/Tradera har gjorts i denna release.
