# FlipFynd v0.6.6 – Sold Comp Collector & historikskydd

## Varför denna release
v0.6.5 kunde importera verifierade avslut, men sold-comp-biblioteket växte bara genom manuell CSV/JSON-import. v0.6.6 lägger till en konservativ collector som kan återanvända explicit såld-evidens som redan finns i lokala snapshots/inlästa data – utan att någonsin anta att `ended`, `closed` eller `completed` betyder såld.

## Ändrat
- Ny `src/sold_comp_collector.py`.
- Collector accepterar endast:
  - explicit positivt `sold_price`, eller
  - explicit såld-status **plus** ett faktiskt pris.
- `ended`, `closed` och vanlig `completed` utan såld-evidens ignoreras.
- Befintliga valuta-/anti-hallucination-regler återanvänds: utländsk valuta kräver explicit SEK-belopp eller explicit FX-kurs.
- Dubbletter slås ihop via samma sold-comp-ID/fingerprint som importmotorn.
- En dubblett får komplettera saknad metadata (datum, säljare, sport m.m.) men får inte skriva över realiserat pris.
- Ny CLI `collect_sold_comps.py` kan skanna en eller flera lokala JSON-snapshots och samla verifierbara avslut till `data/sold_comps.json`.
- Ny adminsektion **Samla verifierade avslut** i Streamlit.
- Visar antal sold comps i aktuell datamiljö.
- Knapp för att samla explicit sold-evidens från redan inlästa annonser.
- Exportknapp för hela sold-comp-biblioteket till JSON.
- UI förklarar uttryckligen att Streamlit Clouds lokala filsystem inte är permanent lagring mellan alla deploys/omstarter.
- Cachemodell uppdaterad till `flip_v6_sold_comp_collector`.
- Synligt versionsnummer: v0.6.6.

## QA som faktiskt körts
- `python -m compileall -q .` – godkänd.
- `python -m unittest discover -s tests -v` – 115/115 tester godkända.
- Collector-CLI smoke-test körd separat mot temporär JSON och temporär output.

## Inte verifierat
- Ingen live-verifiering på Streamlit.
- Tradera-inläsningen har ännu inte verifierats leverera explicit sold-status/sold_price; collectorn kan därför mycket väl hitta 0 avslut i dagens live-data.
- Ingen automatisk extern sold-källa (Tradera-avslut/eBay sold/Cardmarket) är ansluten.
- Ingen extern permanent databas är inkopplad. Exporten minskar risken att förlora biblioteket, men är inte samma sak som persistent cloud storage.

## Nästa högst värderade steg
Hårdgör comp-matchningen innan sold-data får större påverkan: grade/graderingsbolag, exakt serial numbering, parallel, card number, season och identitetskonflikter ska kunna diskvalificera en comp i stället för att bara ge ett poängavdrag. Det minskar risken att två visuellt/nominellt liknande men prismässigt helt olika kort blandas ihop.
