# FlipFynd v0.12.51 – Top-3 Diversity & Multi-Source Comp Consensus

## Varför Gretzky kunde ta plats 1, 2 och 3
Top-3-rankningen sorterade främst på tier, säkerhet och fyndpotential utan spelar-diversitet. Samtidigt kunde säkerhetsmåttet få en tydlig bonus av säker spelaridentifiering. En superstjärna som Wayne Gretzky kunde därför dominera flera platser även när exakt kortidentitet och SOLD-underlag var svagt.

## Fixar
- Top-3 försöker nu välja olika spelare när jämförbara alternativ finns.
- Samma spelare får flera platser först när det saknas tillräckliga alternativa kandidater.
- Top-3:s visade säkerhet kapas till 54/100 när exakt kortidentitet inte är verifierad.
- Utan verifierade exact SOLD-comps kapas den vidare till 49/100; med bara en comp till 59/100.
- Den råa interna confidence-signalen sparas separat så ingen analysinformation försvinner.

## Multi-Source Comp Consensus
- Ny `src/multi_source_comp_consensus.py`.
- Konsensus räknar endast exact + explicit verifierade realiserade sales.
- Tradera hålls separat som lokal svensk prisbild och får en liten lokal relevansvikt.
- Internationell median visas separat så svensk/internationell avvikelse kan upptäckas.
- SportsCardsPro/price-guide-data räknas inte som individuella sales utan uttrycklig sale-evidens.
- Researchplanen utökad med Tradera, Fanatics Collect och COMC utöver eBay, Card Ladder, 130 Point och SportsCardsPro.

## Säkerhetsprincip
Aktiva Tradera-annonser är utbud/asking, inte SOLD-comps. Ingen extern webbplats skrapas automatiskt av denna release.

## QA
1006 tester passerar. `compileall` OK.
