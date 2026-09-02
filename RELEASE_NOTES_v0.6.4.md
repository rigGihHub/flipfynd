# FlipFynd v0.6.4 – Sold Comp Foundation

## Varför denna release
Den största kvarvarande värderingsrisken var att lokala jämförelser huvudsakligen bestod av aktiva annonser. Ett begärt pris är inte samma sak som ett realiserat försäljningspris.

## Ändrat
- Infört tydlig marknadsstatus för comps: `sold` eller `asking`.
- En annons räknas aldrig som såld enbart för att den är avslutad/stängd. Såld-status kräver explicit såld-markering eller explicit `sold_price`.
- Sålda comps prioriteras före aktiva annonser när minst två tillräckligt matchande sålda observationer finns.
- Aktiva annonser används fortsatt konservativt som sekundärt marknadsstöd.
- Sålda comps får högre vikt i värderingen än asking prices.
- Äldre sålda comps får lägre vikt än färska försäljningar.
- Comp-detaljer sparar plattform, datum, ålder, matchningskvalitet, pris och provenance.
- Separata räknare för verifierade sålda comps och aktiva jämförelseannonser.
- UI visar om värderingen faktiskt bygger på sålda comps eller endast aktiva annonser.
- UI kan visa individuella jämförelseobjekt i full analys.
- Ny separat fil `data/sold_comps.json` för historiska försäljningar. Den blandas inte in i listan över aktiva köpkandidater.
- Analyscachens modellversion uppdaterad så gamla analyser inte återanvänds efter värderingsändringen.

## Viktig begränsning
Denna release bygger infrastrukturen för riktiga sold comps men hämtar ännu inte automatiskt avslut från Tradera/eBay/Cardmarket. Om `data/sold_comps.json` är tom används fortfarande aktiva annonser konservativt som stöd.

## QA
- `python -m compileall -q .`: godkänd.
- `python -m unittest discover -s tests -v`: 99 av 99 tester godkända.
- Ingen live-verifiering mot Streamlit eller externa marknadsplatser genomförd.
