# FlipFynd v0.11.6 – Search Pipeline Fix & Diagnostics

## Varför
En användare kunde ha hundratals hockeyannonser inlästa men ändå se 0 kandidater. UI:t visade bara ett generellt filtermeddelande och kunde dessutom visa ett gammalt tomt resultat efter att ny data hade hämtats.

## Ändringar
- Ny steg-för-steg-diagnostik för sökpipelinen: dataset → prestandaskydd → sport → giltigt pris → budget → sökning → annonsform → specialfilter → analyserade kandidater.
- Tydliga felorsaker när ett steg går till noll.
- Annonscachen använder nu datasetversion i cache-nyckeln, så page-by-page-hämtning syns utan att vänta på hela subprocessen.
- Gamla sökresultat rensas automatiskt när annonsfilen ändras. En gammal nolla ska alltså inte ligga kvar efter en lyckad hämtning.
- Konservativ reparation av gammal marknadstäckning när state påstår djup täckning men verifierade Tradera-länkar bara stödjer de första sidorna för sporten.
- UI:t skiljer mellan "inga analyserbara kandidater" och "resultat finns men döljs av visningsfilter".

## Säkerhet
Diagnostiken ändrar inte värdering, ranking, maxbud eller köpbeslut. Marknadstäckning repareras bara vid en tydlig legacy-mismatch.
