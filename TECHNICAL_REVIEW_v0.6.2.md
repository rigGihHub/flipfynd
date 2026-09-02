# Teknisk genomgång av FlipFynd v0.6.2

## Sammanfattning
Kodbasen har redan flera relevanta skydd för verklig flip-potential: konservativ okänd frakt, auktionsbuffert, efterfrågestyrda premiumbonusar, rookie-/graderingsguardrails, lot-skydd, duplikatfilter, kortidentitet, fyndsäkerhet och riskjusterad rankning. Det är implementerat och täcks i stor utsträckning av enhetstester.

Den största kvalitetsbegränsningen är fortfarande marknadsvärderingen. De lokala comparable-annonserna är aktiva Tradera-annonser, alltså asking prices och inte verifierade avslut. Koden väger dem medvetet försiktigt, men detta innebär att appens beräknade marknadsvärde ännu inte är en sold-comps-värdering. Detta bör vara nästa större datamässiga fokus efter identitetsförbättringen i v0.6.3.

## Projektstruktur och arkitektur
- `app.py`: Streamlit-UI, filter, snabb/full analys, cacheanvändning och fetch-kontroller.
- `src/analyzer.py`: huvuddelen av heuristik, värderingslogik, risk, vinst, ROI, beslut, maxpris och rankning.
- `src/card_parser.py`: titelbaserad parsing av set, säsong, kortnummer, serialisering, parallel, rookieprogram, gradering och lot.
- `src/market_analysis.py`: lokal comparable-motor med likhetspoäng, outlier-hantering och duplikatskydd.
- `src/player_market.py` + `data/player_market.json`: hårdkodad/filbaserad spelarefterfrågan.
- `src/tradera_fetcher.py` + `fetch_tradera_pages.py`: Playwright-crawl av Tradera med sidvis checkpoint och statusfil.
- `src/analysis_cache.py`: JSON-baserad analyscache med modellversion och max 4 000 poster.
- `src/ai_market_analysis.py`: OpenAI-baserad modul finns men används inte i huvudflödet.

## Datainsamling från Tradera
Implementerat:
- Separata kategorier för hockey och fotboll.
- Sidvis crawl, smart stopp efter kända sidor och säkerhetsgräns.
- Sidvis persistens till `tradera_data.json`.
- Hämtning av titel, pris, frakt, säljare, länk, omgivande listtext, sida och kategori.

Begränsningar:
- Huvudcrawlern hämtar kategorisidor, inte den fulla objektsidan för varje kort.
- Beskrivning, bilder, exakt sluttid, budhistorik och säljarstatistik hämtas inte strukturerat i den nuvarande item-modellen.
- Cloud-lagringen är filbaserad och därmed inte en robust permanent databas på Streamlit Community Cloud.

## Kortidentifiering före v0.6.3
Styrkor:
- Spelarmatchning med alias och försiktig fuzzy-matchning.
- Set/program, säsongsnormalisering, kortnummer, serialisering, rookieprogram, parallel, gradering och lot.
- Sammanhållen `card_identity` används i comparable-likhet.

Svaghet som prioriterades:
- Den mesta identiteten byggdes från `titel` trots att crawlern redan sparar `raw_text`.
- Det saknades fältnivå-proveniens och explicit konfliktkontroll mellan rubrik och övrig annonsinformation.

Detta åtgärdas i v0.6.3.

## Marknadsvärdering och comparable sales
Nuvarande beteende:
- Liknande lokala annonser väljs genom identitets-/spelar-/set-/variantpoäng.
- Relists dedupliceras.
- Pris + frakt används konsekvent.
- Outliers tas bort och median/trimmed median används.
- Aktiva comps får maximalt 50 % vikt i estimatet och lägre vikt vid svagt underlag.

Kritisk begränsning:
- Detta är inte faktiska avslut. `compute_comp_weight()` dokumenterar själv att underlaget är asking prices.
- Ålder på comps, plattform, region och faktiskt försäljningsdatum saknas.
- UI visar inte de individuella compsen med pris/datum/matchningsgrad.

## Fyndmodell
Positivt:
- Nettovinst, ROI, riskjusterad vinst, säljsannolikhet, likviditet och spelarefterfrågan används.
- Premiumegenskaper skalas mot verklig spelarefterfrågan i stället för att dominera automatiskt.
- Billiga kapital-effektiva flips kan rankas högt.
- Fyndsäkerheten påverkar rankningen.

Begränsningar:
- `compute_profit()` har fasta antaganden: 8 % säljavgift, 18/36 kr utgående frakt och 3 kr emballage. Detta är inte användarkonfigurerat eller plattformsdifferentierat.
- Likviditet och säljsannolikhet är fortfarande heuristiska och bygger inte på mätt historisk omsättningstid.
- Spelarvärdet är filbaserat och inte automatiskt uppdaterat med verifierade aktuella fakta.

## Cache och prestanda
- Tvåstegsanalys används: alla kandidater snabbscannas, endast topplistan får full comparable-analys.
- Resultat cacheas på länk, titel, pris, frakt, raw text, dataversion och analysläge.
- Detta är en bra riktning för att undvika onödiga analyser.
- Cache är lokal JSON och inte permanent/replikerad datalagring.
- Modellversion måste höjas vid semantiska analysändringar; detta görs i v0.6.3 för att undvika gamla resultat.

## UI
Styrkor:
- Köpbeslut, total kostnad, resale, nettovinst, maxbud, fyndsäkerhet och auktionsstrategi är redan prioriterade.
- Avancerade filter är undanlagda.

Saknas jämfört med målbilden:
- Bild på kortet.
- Tydlig fyndpoäng 0–100 som separat begrepp från fyndsäkerhet/rank_score.
- Tid kvar/slutar snart-vy.
- Nya Köp nu-fynd-vy.
- Individuella comps med provenance.
- Feedback loop/backtesting.

## Hårdkodat och teknisk skuld
- Setvikter och premiumset ligger i Python-konstanter.
- Spelarmarknad ligger i JSON med manuella scores.
- Kostnadsantaganden är hårdkodade.
- `analyzer.py` är stor och innehåller flera ansvar; bör delas först när funktionell nytta motiverar det.
- Både `src/__init__.py` och felstavade `src/_init_.py` finns.
- Äldre hjälpskript (`fetch_data.py`, `read_html.py`, `visa_data.py`) verkar ligga vid sidan av produktionsflödet och bör senare klassificeras/rensas.
- AI-modulen finns men är inte inkopplad. Den bör inte kopplas in bara för att den finns; verifierad sold-data är mer värdefull.

## Prioriterad utvecklingsordning från denna genomgång
1. Evidensbaserad kortidentifiering och konfliktskydd — v0.6.3.
2. Sold-comps-datamodell + provenance och strikt separation mellan sold/asking.
3. Värdering med low/base/high baserat på sold comps, ålder och matchningsgrad.
4. Likviditet från observerad historik i stället för enbart heuristik.
5. Fyndpoäng 0–100 kalibrerad mot backtesting.
6. Strukturerad tid kvar, nya Köp nu och slutar snart.
7. Feedback loop och backtesting.
8. Bildanalys endast som kompletterande identitetsbevis, aldrig som ensam värdekälla.
