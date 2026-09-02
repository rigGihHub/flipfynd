# FlipFynd v0.11.2 – Performance & Smart Crawl

## Varför
Streamlit Cloud throttlade appen efter en första hämtning som växte till över 9 000 aktiva annonser. Samtidigt visade UI:t 0 hockey och tusentals fotbollsannonser.

## Ändrat
- Smart uppdatering är nu hårt begränsad till de 12 nyaste resultatsidorna per sport.
- Smart uppdatering stoppar redan efter 2 hela sidor utan nya annonser.
- Detaljberikning har sänkts från 12 till 6 prioriterade annonser per sport och körning.
- Aktivt dataset begränsas till högst 1 500 annonser per sport.
- Interaktiv fyndanalys använder samma bounded dataset, även om en gammal cloud-runtime fortfarande har en mycket större fil.
- Sport verifieras mot kategori-id i Tradera-annonsens URL (`293316` hockey, `293311` fotboll).
- En annons från fel kategori släpps inte längre igenom en sportcrawl.
- Äldre felaktiga `source_category`-etiketter repareras när datasetet komprimeras.
- UI visar tydligt när prestandaskyddet är aktivt och när hockeydata saknas.
- Full genomsökning finns kvar som avancerat felsökningsläge men markeras som tungt för Streamlit Cloud.

## Säkerhetsprincip
Prestandaskyddet ändrar inte värdering, vinst, ROI, maxbud eller köpbeslut. Det begränsar bara hur mycket aktiv marknadsdata som CPU-bearbetas samtidigt.
